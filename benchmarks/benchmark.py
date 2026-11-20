"""Medição simples de vazão/latência de transferência de arquivo local."""
import argparse
import socket
import time
from pathlib import Path
from protocol import CHUNK_SIZE, send_json, recv_json, recv_exact, sha256, request_signature

def measure(host, port, secret, filename, rounds):
    total_bytes = 0
    latencies = []
    start_all = time.perf_counter()
    for index in range(rounds):
        req = {"command": "GET_CHUNK", "filename": filename, "index": index}
        req["signature"] = request_signature(secret, req)
        start = time.perf_counter()
        with socket.create_connection((host, port), timeout=10) as sock:
            send_json(sock, req)
            header = recv_json(sock)
            if not header.get("ok"):
                raise RuntimeError(header)
            data = recv_exact(sock, header["length"])
            if sha256(data) != header["sha256"]:
                raise RuntimeError("Falha de integridade")
        latencies.append((time.perf_counter() - start) * 1000)
        total_bytes += len(data)
    elapsed = time.perf_counter() - start_all
    print(f"Blocos: {rounds}")
    print(f"Bytes: {total_bytes}")
    print(f"Latência média por bloco: {sum(latencies)/len(latencies):.2f} ms")
    print(f"Vazão média: {total_bytes/max(elapsed, 1e-9)/1024:.2f} KiB/s")
    print("Perda observada na aplicação: 0 blocos não recebidos (TCP retransmite segmentos).")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--host", required=True)
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--secret", default="troque-esta-chave")
    p.add_argument("--file", required=True)
    p.add_argument("--rounds", type=int, default=10)
    a = p.parse_args()
    measure(a.host, a.port, a.secret, a.file, a.rounds)
