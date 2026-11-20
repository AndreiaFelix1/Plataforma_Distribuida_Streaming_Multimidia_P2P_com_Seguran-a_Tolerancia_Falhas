"""Descoberta opcional de peers na LAN por IPv4 multicast."""
import argparse, json, socket, struct, threading, time, uuid

GROUP="239.255.42.99"; PORT=5007
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--peer-port",type=int,required=True)
    p.add_argument("--name",default=None)
    a=p.parse_args()
    alias=a.name or "peer-"+uuid.uuid4().hex[:8]
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    sock.bind(("",PORT))
    mreq=struct.pack("4sl",socket.inet_aton(GROUP),socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP,mreq)
    sock.settimeout(1)
    print(f"[MULTICAST] {alias}; grupo={GROUP}:{PORT}; porta P2P={a.peer_port}")
    last=0
    try:
        while True:
            now=time.time()
            if now-last>=5:
                msg=json.dumps({"type":"STREAM_P2P_DISCOVERY","alias":alias,"p2p_port":a.peer_port,"ts":now}).encode()
                sock.sendto(msg,(GROUP,PORT));last=now
            try:
                data,addr=sock.recvfrom(2048)
                msg=json.loads(data.decode())
                if msg.get("type")=="STREAM_P2P_DISCOVERY" and msg.get("alias")!=alias:
                    print(f"[MULTICAST] Peer {msg.get('alias')} em {addr[0]}:{msg.get('p2p_port')}")
            except socket.timeout:pass
    except KeyboardInterrupt:pass
    finally:sock.close()
if __name__=="__main__":main()
