"""Protocolo de mensagens e utilitários de segurança do StreamP2P."""
import hashlib
import hmac
import json
import socket
import struct

CHUNK_SIZE = 256 * 1024
MAX_HEADER = 1024 * 1024

def send_json(sock: socket.socket, obj: dict) -> None:
    data = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    if len(data) > MAX_HEADER:
        raise ValueError("Cabeçalho excede o limite")
    sock.sendall(struct.pack("!I", len(data)) + data)

def recv_exact(sock: socket.socket, size: int) -> bytes:
    parts = []
    remaining = size
    while remaining:
        block = sock.recv(remaining)
        if not block:
            raise ConnectionError("Conexão encerrada durante a recepção")
        parts.append(block)
        remaining -= len(block)
    return b"".join(parts)

def recv_json(sock: socket.socket) -> dict:
    size = struct.unpack("!I", recv_exact(sock, 4))[0]
    if size > MAX_HEADER:
        raise ValueError("Cabeçalho recebido excede o limite")
    return json.loads(recv_exact(sock, size).decode("utf-8"))

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sign(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

def verify_signature(secret: str, message: bytes, signature: str) -> bool:
    return hmac.compare_digest(sign(secret, message), signature)

def request_signature(secret: str, payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sign(secret, canonical)
