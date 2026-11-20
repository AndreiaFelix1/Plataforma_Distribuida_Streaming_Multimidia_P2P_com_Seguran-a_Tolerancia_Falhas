"""Benchmark UDP com ACK e retransmissão na aplicação (stop-and-wait).

Terminal A: python3 udp_benchmark.py server --host 0.0.0.0 --port 9900
Terminal B: python3 udp_benchmark.py client --host IP_DO_SERVIDOR --port 9900 --mb 5
A perda simulada com tc netem permite observar retransmissões no cliente.
"""
import argparse, hashlib, socket, struct, time, csv, os

MAGIC = b"SP2P"
DATA = 1
ACK = 2
HEADER = struct.Struct("!4sBI32s")
PAYLOAD_SIZE = 1000
TIMEOUT = 0.25
MAX_RETRIES = 20

def run_server(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"[UDP SERVER] {host}:{port}")
    received = set(); total = 0; start = time.perf_counter()
    try:
        while True:
            packet, addr = sock.recvfrom(2048)
            if len(packet) < HEADER.size: continue
            magic, kind, seq, digest = HEADER.unpack(packet[:HEADER.size])
            payload = packet[HEADER.size:]
            if magic != MAGIC or kind != DATA: continue
            if hashlib.sha256(payload).digest() != digest: continue
            if seq not in received:
                received.add(seq); total += len(payload)
            ack = HEADER.pack(MAGIC, ACK, seq, digest)
            sock.sendto(ack, addr)
            if seq == 0:
                start = time.perf_counter()
            if seq % 100 == 0:
                print(f"[UDP SERVER] pacotes únicos={len(received)} bytes={total}")
    except KeyboardInterrupt:
        elapsed=max(time.perf_counter()-start,1e-9)
        print(f"Recebidos={len(received)}; bytes={total}; vazão={total/elapsed/1024:.2f} KiB/s")
    finally: sock.close()

def run_client(host, port, megabytes, csv_path=None):
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.settimeout(TIMEOUT)
    payload=b"X"*PAYLOAD_SIZE
    total_bytes=megabytes*1024*1024
    count=(total_bytes+PAYLOAD_SIZE-1)//PAYLOAD_SIZE
    retransmissions=0; start=time.perf_counter()
    for seq in range(count):
        part=payload if seq<count-1 else b"X"*(total_bytes-seq*PAYLOAD_SIZE)
        digest=hashlib.sha256(part).digest()
        packet=HEADER.pack(MAGIC,DATA,seq,digest)+part
        success=False
        for attempt in range(MAX_RETRIES):
            sock.sendto(packet,(host,port))
            try:
                ack,_=sock.recvfrom(256)
                if len(ack)>=HEADER.size:
                    magic,kind,ack_seq,ack_hash=HEADER.unpack(ack[:HEADER.size])
                    if magic==MAGIC and kind==ACK and ack_seq==seq and ack_hash==digest:
                        success=True;retransmissions+=attempt;break
            except socket.timeout: pass
        if not success:
            raise TimeoutError(f"Pacote {seq} não confirmado após {MAX_RETRIES} tentativas")
        if seq%100==0: print(f"\rEnviados {seq+1}/{count} pacotes",end="",flush=True)
    elapsed=max(time.perf_counter()-start,1e-9);sock.close()
    throughput=total_bytes/elapsed/1024; avg_latency=(elapsed/count)*1000
    print(f"\nUDP confiável na aplicação: bytes={total_bytes}; tempo={elapsed:.3f}s; "
          f"vazão={throughput:.2f} KiB/s; retransmissões={retransmissions}; "
          f"latência média aproximada por datagrama={avg_latency:.2f} ms")
    if csv_path:
        exists=os.path.exists(csv_path)
        with open(csv_path,'a',newline='') as f:
            w=csv.writer(f)
            if not exists:w.writerow(['protocolo','bytes','tempo_s','throughput_KiB_s','latencia_media_ms','blocos','retransmissoes'])
            w.writerow(['UDP-stop-and-wait',total_bytes,round(elapsed,6),round(throughput,3),round(avg_latency,3),count,retransmissions])

if __name__=="__main__":
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="mode",required=True)
    s=sub.add_parser("server");s.add_argument("--host",default="0.0.0.0");s.add_argument("--port",type=int,default=9900)
    c=sub.add_parser("client");c.add_argument("--host",required=True);c.add_argument("--port",type=int,default=9900);c.add_argument("--mb",type=int,default=5);c.add_argument("--csv",default="resultados_transporte.csv")
    a=p.parse_args()
    if a.mode=="server":run_server(a.host,a.port)
    else:run_client(a.host,a.port,a.mb,a.csv)
