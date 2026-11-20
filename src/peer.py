"""Cliente/peer: registro, descoberta, servidor P2P e recepção em blocos."""
import argparse
import hashlib
import json
import os
import socket
import ssl
import threading
import time
from pathlib import Path
from protocol import (CHUNK_SIZE, send_json, recv_json, recv_exact, sha256,
                      request_signature, verify_signature)

class Peer:
    def __init__(self, server_host="127.0.0.1", server_port=9000,
                 listen_host="0.0.0.0", listen_port=0, secret=None,
                 media_dir="media", download_dir="downloads", tls=False, ca_cert=None, certfile=None, keyfile=None,
                 relay_host=None, relay_port=None):
        self.server_host, self.server_port = server_host, server_port
        self.listen_host, self.listen_port = listen_host, listen_port
        self.secret = secret or os.getenv("STREAM_SECRET", "troque-esta-chave")
        self.media_dir, self.download_dir = Path(media_dir), Path(download_dir)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.tls = tls
        # Relay opcional: o consumidor conecta ao relay, que encaminha o fluxo ao fornecedor.
        self.relay_host, self.relay_port = relay_host, relay_port
        self.ssl_context = None
        if tls:
            if not ca_cert:
                raise ValueError("TLS exige o certificado confiável --ca-cert")
            self.ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_cert)
            # Certificado de laboratório compartilhado pelos nós; a cadeia é validada pela CA local.
            # Em produção, use certificados individuais e habilite validação de hostname.
            self.ssl_context.check_hostname = False
            if not certfile or not keyfile:
                raise ValueError("TLS P2P exige --cert e --key em cada peer")
            self.server_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.server_ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            self.server_ssl_context.load_cert_chain(certfile, keyfile)
        else:
            self.server_ssl_context = None
        self.peer_id = None
        self.running = True
        self.server_socket = None

    def local_files(self):
        # Compartilha tanto a biblioteca original quanto downloads já concluídos.
        names = set()
        for folder in (self.media_dir, self.download_dir):
            names.update(p.name for p in folder.iterdir() if p.is_file() and not p.name.endswith((".part", ".json")))
        return sorted(names)

    def shared_catalog(self):
        entries = []
        for name in self.local_files():
            path = self.shared_file(name)
            if path is not None:
                entries.append({"name": name, "size": path.stat().st_size})
        return entries

    def shared_file(self, filename):
        safe_name = Path(filename).name
        for folder in (self.media_dir, self.download_dir):
            candidate = folder / safe_name
            if candidate.is_file():
                return candidate
        return None

    def control(self, command, **kwargs):
        family = socket.AF_INET6 if ":" in self.server_host else socket.AF_INET
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.settimeout(8)
            sock.connect((self.server_host, self.server_port))
            if self.ssl_context:
                sock = self.ssl_context.wrap_socket(sock, server_hostname=self.server_host)
            send_json(sock, {"command": command, "secret": self.secret, **kwargs})
            return recv_json(sock)

    def start(self):
        family = socket.AF_INET6 if ":" in self.listen_host else socket.AF_INET
        self.server_socket = socket.socket(family, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if family == socket.AF_INET6:
            self.server_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        self.server_socket.bind((self.listen_host, self.listen_port))
        self.server_socket.listen(50)
        self.listen_port = self.server_socket.getsockname()[1]
        # Endereço anunciado: em laboratório, informe --advertise-host com IP alcançável.
        self.advertise_host = self.advertise_host_arg
        result = self.control("REGISTER", host=self.advertise_host,
                              port=self.listen_port, files=self.shared_catalog())
        if not result.get("ok"):
            raise RuntimeError(f"Falha no registro: {result}")
        self.peer_id = result["peer_id"]
        print(f"[PEER] Registrado como {self.peer_id}; porta P2P={self.listen_port}")
        threading.Thread(target=self.accept_loop, daemon=True).start()
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()

    def accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                if self.ssl_context:
                    conn = self.server_ssl_context.wrap_socket(conn, server_side=True)
                threading.Thread(target=self.handle_p2p, args=(conn, addr), daemon=True).start()
            except OSError:
                break

    def handle_p2p(self, conn, addr):
        try:
            conn.settimeout(20)
            req = recv_json(conn)
            signature = req.pop("signature", "")
            if not verify_signature(self.secret,
                    json.dumps(req, sort_keys=True, separators=(",", ":")).encode(), signature):
                send_json(conn, {"ok": False, "error": "assinatura_invalida"})
                return
            if req.get("command") != "GET_CHUNK":
                send_json(conn, {"ok": False, "error": "comando_invalido"})
                return
            path = self.shared_file(req["filename"])
            if path is None:
                send_json(conn, {"ok": False, "error": "conteudo_indisponivel"})
                return
            index = int(req["index"])
            with path.open("rb") as f:
                f.seek(index * CHUNK_SIZE)
                data = f.read(CHUNK_SIZE)
            if not data:
                send_json(conn, {"ok": False, "error": "bloco_inexistente"})
                return
            digest = sha256(data)
            payload = {"ok": True, "length": len(data), "sha256": digest}
            payload["hmac"] = request_signature(self.secret, payload)
            send_json(conn, payload)
            conn.sendall(data)
        except (OSError, ValueError, KeyError, ConnectionError) as exc:
            try:
                send_json(conn, {"ok": False, "error": str(exc)})
            except OSError:
                pass
        finally:
            conn.close()

    def heartbeat_loop(self):
        while self.running:
            try:
                self.control("HEARTBEAT", peer_id=self.peer_id, files=self.shared_catalog())
            except OSError:
                print("[PEER] Servidor de controle indisponível; nova tentativa em 5s")
            time.sleep(10)

    def list_content(self):
        result = self.control("LIST")
        for item in result.get("catalog", []):
            print(f'{item["name"]} ({item["size"]} bytes)')
        return result.get("catalog", [])

    def discover(self, filename):
        return self.control("DISCOVER", filename=filename).get("peers", [])

    def get_chunk(self, peer, filename, index):
        family = socket.AF_INET6 if ":" in peer["host"] else socket.AF_INET
        connect_host = self.relay_host or peer["host"]
        connect_port = int(self.relay_port) if self.relay_host else int(peer["port"])
        family = socket.AF_INET6 if ":" in connect_host else socket.AF_INET
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.settimeout(20)
            sock.connect((connect_host, connect_port))
            if self.relay_host:
                # O relay recebe o destino assinado e faz o encaminhamento TCP opaco.
                route = {"command": "RELAY_CONNECT", "host": peer["host"], "port": int(peer["port"])}
                route["signature"] = request_signature(self.secret, route)
                send_json(sock, route)
                ready = recv_json(sock)
                if not ready.get("ok"):
                    raise RuntimeError(ready.get("error", "relay recusou a rota"))
            if self.ssl_context:
                sock = self.ssl_context.wrap_socket(sock, server_hostname=peer["host"])
            req = {"command": "GET_CHUNK", "filename": filename, "index": index}
            req["signature"] = request_signature(self.secret, req)
            send_json(sock, req)
            header = recv_json(sock)
            if not header.get("ok"):
                raise RuntimeError(header.get("error", "erro no peer"))
            received_hmac = header.pop("hmac")
            if not verify_signature(self.secret,
                    json.dumps(header, sort_keys=True, separators=(",", ":")).encode(),
                    received_hmac):
                raise RuntimeError("HMAC do bloco inválido")
            data = recv_exact(sock, int(header["length"]))
            if sha256(data) != header["sha256"]:
                raise RuntimeError("SHA-256 divergente")
            return data

    def download(self, filename, on_chunk=None):
        # Sanitiza o nome para impedir path traversal.
        filename = Path(filename).name
        peers = self.discover(filename)
        if not peers:
            raise RuntimeError("Nenhum peer disponível para esse conteúdo.")
        item = next((x for x in self.list_content() if x["name"] == filename), None)
        if not item:
            raise RuntimeError("Conteúdo não consta no catálogo.")
        size = int(item["size"])
        total_chunks = (size + CHUNK_SIZE - 1) // CHUNK_SIZE
        output = self.download_dir / filename
        temp = output.with_suffix(output.suffix + ".part")
        progress_file = temp.with_suffix(temp.suffix + ".json")
        try:
            saved = json.loads(progress_file.read_text(encoding="utf-8"))
            completed = {int(k): v for k, v in saved.items()}
        except (OSError, ValueError, TypeError):
            completed = {}
        started = time.perf_counter()
        received = 0
        failures = 0
        mode = "r+b" if temp.exists() else "w+b"
        with temp.open(mode) as f:
            f.truncate(size)
            # Valida novamente os blocos persistidos antes de confiar no estado de retomada.
            for index in list(completed):
                expected = min(CHUNK_SIZE, size - index * CHUNK_SIZE)
                f.seek(index * CHUNK_SIZE)
                block = f.read(expected)
                if len(block) != expected or sha256(block) != completed[index]:
                    del completed[index]
            for index in range(total_chunks):
                if index in completed:
                    if on_chunk:
                        f.seek(index * CHUNK_SIZE)
                        cached = f.read(min(CHUNK_SIZE, size - index * CHUNK_SIZE))
                        on_chunk(index, cached, size, total_chunks)
                    continue
                success = False
                candidates = peers[:]
                while candidates and not success:
                    peer = candidates.pop(0)
                    try:
                        block = self.get_chunk(peer, filename, index)
                        f.seek(index * CHUNK_SIZE)
                        f.write(block)
                        f.flush()
                        completed[index] = sha256(block)
                        received += len(block)
                        progress_file.write_text(json.dumps(completed), encoding="utf-8")
                        if on_chunk:
                            on_chunk(index, block, size, total_chunks)
                        success = True
                    except (OSError, RuntimeError, ConnectionError) as exc:
                        failures += 1
                        print(f"[PEER] Peer {peer['id'][:8]} falhou no bloco {index}: {exc}")
                if not success:
                    print(f"[PEER] Download interrompido no bloco {index}. Execute novamente para retomar.")
                    return
                print(f"\r[STREAM] Bloco {index + 1}/{total_chunks}", end="", flush=True)
        # Hash final adicional para detectar inconsistências no arquivo completo.
        os.replace(temp, output)
        try:
            progress_file.unlink()
        except OSError:
            pass
        elapsed = max(time.perf_counter() - started, 1e-9)
        throughput = received / elapsed
        self.last_download_metrics = {
            "filename": filename, "bytes_received": received, "elapsed_seconds": elapsed,
            "throughput_bytes_sec": throughput, "failed_attempts": failures,
            "chunks": total_chunks
        }
        print(f"\n[OK] Salvo em {output}; vazão={throughput/1024:.2f} KiB/s; "
              f"tempo={elapsed:.3f}s; falhas={failures}")
    def shutdown(self):
        self.running = False
        try:
            self.control("UNREGISTER", peer_id=self.peer_id)
        except OSError:
            pass
        if self.server_socket:
            self.server_socket.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=9000)
    parser.add_argument("--listen-host", default="0.0.0.0")
    parser.add_argument("--listen-port", type=int, default=0)
    parser.add_argument("--advertise-host", default="127.0.0.1")
    parser.add_argument("--media", default="media")
    parser.add_argument("--downloads", default="downloads")
    parser.add_argument("--secret", default=None)
    parser.add_argument("--tls", action="store_true", help="Habilita TLS no controle e no P2P")
    parser.add_argument("--ca-cert", default="certs/server.crt")
    parser.add_argument("--cert", default="certs/server.crt")
    parser.add_argument("--key", default="certs/server.key")
    parser.add_argument("--relay-host", default=None, help="Relay de privacidade (opcional)")
    parser.add_argument("--relay-port", type=int, default=9200)
    args = parser.parse_args()
    peer = Peer(args.server, args.server_port, args.listen_host, args.listen_port,
                args.secret, args.media, args.downloads, args.tls, args.ca_cert, args.cert, args.key,
                relay_host=args.relay_host, relay_port=args.relay_port)
    peer.advertise_host_arg = args.advertise_host
    peer.start()
    print("Comandos: list | download NOME | quit")
    try:
        while True:
            command = input("stream> ").strip()
            if command == "list":
                peer.list_content()
            elif command.startswith("download "):
                peer.download(command[len("download "):].strip())
            elif command in ("quit", "exit"):
                break
            elif command:
                print("Comando inválido.")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        peer.shutdown()

if __name__ == "__main__":
    main()
