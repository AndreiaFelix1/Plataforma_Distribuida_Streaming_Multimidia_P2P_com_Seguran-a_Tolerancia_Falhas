#!/usr/bin/env python3
"""
Relay TCP para privacidade de metadados em laboratório.
O consumidor conecta ao relay; o relay abre a conexão com o peer fornecedor
e encaminha os bytes sem interpretar o protocolo P2P.
Não é Tor, mixnet ou anonimato forte: o relay conhece os dois extremos.
"""
import argparse, json, socket, threading
from protocol import recv_json, send_json, request_signature, verify_signature

def pipe(a, b):
    def pump(src, dst):
        try:
            while True:
                data = src.recv(65536)
                if not data:
                    break
                dst.sendall(data)
        except OSError:
            pass
        finally:
            try: dst.shutdown(socket.SHUT_WR)
            except OSError: pass
    t1=threading.Thread(target=pump,args=(a,b),daemon=True)
    t2=threading.Thread(target=pump,args=(b,a),daemon=True)
    t1.start(); t2.start(); t1.join(); t2.join()

class Relay:
    def __init__(self, host, port, secret, allowed):
        self.host,self.port,self.secret=host,port,secret
        self.allowed=set(allowed)

    def handle(self, client):
        upstream=None
        try:
            client.settimeout(15)
            route=recv_json(client)
            signature=route.pop("signature","")
            canonical=json.dumps(route,sort_keys=True,separators=(",",":")).encode()
            if not verify_signature(self.secret,canonical,signature):
                send_json(client,{"ok":False,"error":"assinatura_do_relay_invalida"}); return
            if route.get("command")!="RELAY_CONNECT":
                send_json(client,{"ok":False,"error":"comando_invalido"}); return
            host=str(route.get("host",""))
            port=int(route.get("port",0))
            if f"{host}:{port}" not in self.allowed:
                send_json(client,{"ok":False,"error":"destino_nao_autorizado"}); return
            family=socket.AF_INET6 if ":" in host else socket.AF_INET
            upstream=socket.socket(family,socket.SOCK_STREAM)
            upstream.settimeout(15); upstream.connect((host,port)); upstream.settimeout(None)
            client.settimeout(None)
            send_json(client,{"ok":True})
            pipe(client,upstream)
        except (OSError,ValueError,KeyError,ConnectionError,json.JSONDecodeError) as e:
            try: send_json(client,{"ok":False,"error":str(e)})
            except OSError: pass
        finally:
            try: client.close()
            except OSError: pass
            if upstream:
                try: upstream.close()
                except OSError: pass

    def serve(self):
        family=socket.AF_INET6 if ":" in self.host else socket.AF_INET
        with socket.socket(family,socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            server.bind((self.host,self.port)); server.listen(100)
            print(f"[RELAY] Escutando em {self.host}:{self.port}")
            print("[RELAY] Destinos autorizados:",", ".join(sorted(self.allowed)))
            while True:
                conn,addr=server.accept()
                threading.Thread(target=self.handle,args=(conn,),daemon=True).start()

if __name__=="__main__":
    ap=argparse.ArgumentParser(description="Relay TCP de privacidade para experimento")
    ap.add_argument("--host",default="127.0.0.1")
    ap.add_argument("--port",type=int,default=9200)
    ap.add_argument("--secret",default=None)
    ap.add_argument("--allow",action="append",required=True,help="Destino permitido HOST:PORT; repetir para cada fornecedor")
    a=ap.parse_args()
    import os
    Relay(a.host,a.port,a.secret or os.getenv("STREAM_SECRET","troque-esta-chave"),a.allow).serve()
