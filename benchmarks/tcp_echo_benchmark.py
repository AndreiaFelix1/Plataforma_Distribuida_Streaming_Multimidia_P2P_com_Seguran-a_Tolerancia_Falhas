"""Benchmark TCP de referência para comparar com udp_benchmark.py."""
import argparse, socket, threading, time, hashlib, struct, csv, os
HEADER = struct.Struct('!I32s')

def server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port)); s.listen(10)
        print(f'[TCP SERVER] {host}:{port}')
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle, args=(conn,), daemon=True).start()

def recv_exact(sock, n):
    out=bytearray()
    while len(out)<n:
        b=sock.recv(n-len(out))
        if not b: raise ConnectionError('socket fechado')
        out.extend(b)
    return bytes(out)

def handle(conn):
    with conn:
        try:
            while True:
                raw=conn.recv(4)
                if not raw: return
                while len(raw)<4: raw += recv_exact(conn,4-len(raw))
                size=struct.unpack('!I',raw)[0]
                digest=recv_exact(conn,32); payload=recv_exact(conn,size)
                ok=hashlib.sha256(payload).digest()==digest
                conn.sendall(b'1' if ok else b'0')
        except (ConnectionError,OSError): return

def client(host, port, mb, payload_size, csv_path=None):
    total=mb*1024*1024; payload=b'Z'*payload_size
    sent=0; rtts=[]; start=time.perf_counter()
    with socket.create_connection((host,port),timeout=10) as s:
        while sent<total:
            block=payload[:min(payload_size,total-sent)]
            packet=struct.pack('!I',len(block))+hashlib.sha256(block).digest()+block
            t=time.perf_counter();s.sendall(packet)
            ack=recv_exact(s,1)
            if ack!=b'1': raise RuntimeError('integridade falhou')
            rtts.append((time.perf_counter()-t)*1000);sent+=len(block)
    elapsed=time.perf_counter()-start
    throughput=sent/elapsed/1024; avg_rtt=sum(rtts)/len(rtts)
    print(f'TCP bytes={sent}; tempo={elapsed:.3f}s; throughput={throughput:.2f} KiB/s; RTT médio={avg_rtt:.2f} ms; blocos={len(rtts)}')
    if csv_path:
        exists=os.path.exists(csv_path)
        with open(csv_path,'a',newline='') as f:
            w=csv.writer(f)
            if not exists:w.writerow(['protocolo','bytes','tempo_s','throughput_KiB_s','latencia_media_ms','blocos','retransmissoes'])
            w.writerow(['TCP',sent,round(elapsed,6),round(throughput,3),round(avg_rtt,3),len(rtts),0])

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('server');a.add_argument('--host',default='0.0.0.0');a.add_argument('--port',type=int,default=9901)
    b=sub.add_parser('client');b.add_argument('--host',required=True);b.add_argument('--port',type=int,default=9901);b.add_argument('--mb',type=int,default=5);b.add_argument('--payload-size',type=int,default=1000);b.add_argument('--csv',default='resultados_transporte.csv')
    x=p.parse_args()
    if x.mode=='server':server(x.host,x.port)
    else:client(x.host,x.port,x.mb,x.payload_size,x.csv)
