"""Servidor central de registro, catálogo e descoberta de peers."""
import argparse
import json
import os
import socket
import ssl
import threading
import time
import uuid
from pathlib import Path
from protocol import send_json, recv_json

class ControlServer:
    def __init__(self, host="0.0.0.0", port=9000, secret=None, media_dir="media", tls=False, certfile=None, keyfile=None):
        self.host, self.port = host, port
        self.secret = secret or os.getenv("STREAM_SECRET", "troque-esta-chave")
        self.media_dir = Path(media_dir)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.peers = {}
        self.lock = threading.RLock()
        self.running = True
        self.tls = tls
        self.ssl_context = None
        if tls:
            if not certfile or not keyfile:
                raise ValueError("TLS exige --cert e --key")
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            self.ssl_context.load_cert_chain(certfile, keyfile)

    def catalog(self):
        # Catálogo federado: combina arquivos locais do servidor e metadados dos peers.
        by_name = {}
        for path in sorted(self.media_dir.iterdir()):
            if path.is_file():
                by_name[path.name] = {"name": path.name, "size": path.stat().st_size}
        with self.lock:
            for peer in self.peers.values():
                for entry in peer.get("files", []):
                    if isinstance(entry, dict) and "name" in entry and "size" in entry:
                        by_name.setdefault(entry["name"], {"name": entry["name"], "size": int(entry["size"])})
        return sorted(by_name.values(), key=lambda x: x["name"])

    def handle(self, conn, addr):
        peer_id = None
        try:
            if self.ssl_context:
                conn = self.ssl_context.wrap_socket(conn, server_side=True)
            conn.settimeout(15)
            msg = recv_json(conn)
            if msg.get("secret") != self.secret:
                send_json(conn, {"ok": False, "error": "autenticacao_rejeitada"})
                return
            command = msg.get("command")
            if command == "REGISTER":
                peer_id = str(uuid.uuid4())
                record = {
                    "id": peer_id, "alias": "peer-" + peer_id[:8], "host": msg["host"], "port": int(msg["port"]),
                    "last_seen": time.time(), "files": msg.get("files", [])
                }
                with self.lock:
                    self.peers[peer_id] = record
                send_json(conn, {"ok": True, "peer_id": peer_id, "catalog": self.catalog()})
            elif command == "LIST":
                send_json(conn, {"ok": True, "catalog": self.catalog()})
            elif command == "STATUS":
                with self.lock:
                    active = len(self.peers)
                send_json(conn, {"ok": True, "active_peers": active, "catalog_items": len(self.catalog())})
            elif command == "DISCOVER":
                filename = msg["filename"]
                with self.lock:
                    found = [
                        {k: p[k] for k in ("id", "host", "port")}
                        for p in self.peers.values()
                        if any((entry == filename) or (isinstance(entry, dict) and entry.get("name") == filename)
                               for entry in p.get("files", [])) and time.time() - p["last_seen"] < 45
                    ]
                send_json(conn, {"ok": True, "peers": found})
            elif command == "HEARTBEAT":
                with self.lock:
                    p = self.peers.get(msg.get("peer_id"))
                    if p:
                        p["last_seen"] = time.time()
                        p["files"] = msg.get("files", p["files"])
                send_json(conn, {"ok": bool(p) if 'p' in locals() else False})
            elif command == "UNREGISTER":
                with self.lock:
                    self.peers.pop(msg.get("peer_id"), None)
                send_json(conn, {"ok": True})
            else:
                send_json(conn, {"ok": False, "error": "comando_desconhecido"})
        except (ConnectionError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            try:
                send_json(conn, {"ok": False, "error": str(exc)})
            except OSError:
                pass
        finally:
            conn.close()

    def cleanup_loop(self):
        while self.running:
            time.sleep(10)
            cutoff = time.time() - 45
            with self.lock:
                expired = [pid for pid, p in self.peers.items() if p["last_seen"] < cutoff]
                for pid in expired:
                    del self.peers[pid]

    def serve_forever(self):
        family = socket.AF_INET6 if ":" in self.host else socket.AF_INET
        with socket.socket(family, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if family == socket.AF_INET6:
                server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            server.bind((self.host, self.port))
            server.listen(100)
            print(f"[SERVER] Escutando em {self.host}:{self.port}")
            threading.Thread(target=self.cleanup_loop, daemon=True).start()
            try:
                while self.running:
                    conn, addr = server.accept()
                    threading.Thread(target=self.handle, args=(conn, addr), daemon=True).start()
            except KeyboardInterrupt:
                print("\n[SERVER] Encerrando...")
                self.running = False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--media", default="media")
    parser.add_argument("--tls", action="store_true", help="Habilita TLS no socket de controle")
    parser.add_argument("--cert", default="certs/server.crt")
    parser.add_argument("--key", default="certs/server.key")
    args = parser.parse_args()
    ControlServer(args.host, args.port, media_dir=args.media, tls=args.tls, certfile=args.cert, keyfile=args.key).serve_forever()
