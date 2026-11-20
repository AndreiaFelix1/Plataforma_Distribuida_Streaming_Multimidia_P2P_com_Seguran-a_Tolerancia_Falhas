"""Interface web do StreamP2P. Executa um peer e disponibiliza player HTML5."""
import argparse, json, mimetypes, os, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from peer import Peer
from protocol import CHUNK_SIZE

HTML = r"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>StreamP2P Advanced</title><script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<style>
:root{color-scheme:dark}body{margin:0;background:#101522;color:#eef2ff;font:15px system-ui}
header{padding:24px 5vw;background:#171f31;border-bottom:1px solid #29344b}
h1{margin:0;color:#8dd8ff}main{max-width:1100px;margin:28px auto;padding:0 20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.card,.panel{background:#1a2437;border:1px solid #2c3a55;border-radius:14px;padding:18px}
button{background:#37a6d9;border:0;border-radius:8px;padding:10px 14px;color:#06121c;font-weight:700;cursor:pointer}
button.secondary{background:#33445f;color:#fff}video{width:100%;max-height:65vh;background:#000;border-radius:12px;margin:18px 0}
small,.muted{color:#aab8d0}.stats{display:flex;gap:12px;flex-wrap:wrap}.stat{background:#202d43;padding:12px 16px;border-radius:10px}
#message{margin:12px 0;color:#8dd8ff}a{color:#8dd8ff}
</style></head><body>
<header><h1>▶ StreamP2P Advanced</h1><div class="muted">Streaming distribuído • descoberta P2P • integridade SHA-256</div></header>
<main>
<section class="panel"><h2>Monitoramento do nó</h2><div class="stats" id="stats"></div><div id="message"></div></section>
<h2>Catálogo de conteúdos</h2><div class="grid" id="catalog"></div>
<section class="panel"><h2>Player</h2><div class="muted" id="playing">Selecione um vídeo para reproduzir.</div>
<label>Buffer HLS (segundos):
<select id="bufferSeconds" onchange="setBuffer()"><option value="10">10</option><option value="20" selected>20</option><option value="30">30</option></select></label>
<video id="player" controls playsinline preload="auto"></video>
<div class="muted" id="playbackStats">Buffer: -- • Resolução: -- • Estado: aguardando</div></section>
<section class="panel"><h2>Como adicionar vídeos</h2><p>Copie arquivos MP4 para a pasta <code>media/</code> do peer que irá compartilhá-los. Os demais peers poderão baixá-los pela rede P2P.</p></section>
</main>
<script>
async function refresh(){
 try{
  const r=await fetch('/api/status');const d=await r.json();
  document.getElementById('stats').innerHTML=
   `<div class="stat">ID: <b>${d.peer_alias}</b></div><div class="stat">Peers ativos: <b>${d.active_peers}</b></div><div class="stat">Arquivos locais: <b>${d.local_files.length}</b></div>`;
  const c=await (await fetch('/api/catalog')).json();
  document.getElementById('catalog').innerHTML=c.catalog.map(x=>
   `<article class="card"><h3>${x.name}</h3><p class="muted">${(x.size/1048576).toFixed(2)} MiB • ${x.sources} fonte(s) P2P</p>
   <button onclick="downloadVideo('${encodeURIComponent(x.name)}')">Baixar via P2P</button>
   <button class="secondary" onclick="playVideo('${encodeURIComponent(x.name)}')">MP4 local</button>
   <button class="secondary" onclick="playProgressive('${encodeURIComponent(x.name)}')">▶ Streaming P2P ao vivo</button>
   <button class="secondary" onclick="playHlsP2P('${encodeURIComponent(x.name)}')">HLS adaptativo P2P</button></article>`).join('') || '<p>Nenhum conteúdo encontrado.</p>';
 }catch(e){document.getElementById('message').textContent='Servidor de controle indisponível: '+e}
}
async function downloadVideo(name){
 const filename=decodeURIComponent(name);document.getElementById('message').textContent='Solicitando conteúdo P2P: '+filename;
 const r=await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename})});
 const d=await r.json();document.getElementById('message').textContent=d.message;
 if(d.ok){setTimeout(refresh,1500);setTimeout(()=>playVideo(name),1800)}
}
function playVideo(name){
 const filename=decodeURIComponent(name), video=document.getElementById('player');
 if(window.currentHls){window.currentHls.destroy();window.currentHls=null}
 video.src='/media/'+encodeURIComponent(filename);
 document.getElementById('playing').textContent='Reproduzindo MP4: '+filename;
 video.load();video.play().catch(()=>{});
}
function playProgressive(name){
 const filename=decodeURIComponent(name), video=document.getElementById('player');
 if(window.currentHls){window.currentHls.destroy();window.currentHls=null}
 video.src='/stream/'+encodeURIComponent(filename);
 document.getElementById('playing').textContent='Streaming P2P progressivo: '+filename+' — os blocos são entregues conforme chegam dos peers.';
 video.load();video.play().catch(()=>{});
}
function playHls(name){
 const filename=decodeURIComponent(name), video=document.getElementById('player');
 const stem=filename.replace(/\\.[^.]+$/,'');
 const src='/hls/'+encodeURIComponent(stem)+'/master.m3u8';
 if(window.currentHls){window.currentHls.destroy();window.currentHls=null}
 document.getElementById('playing').textContent='HLS adaptativo: '+filename+' (requer rendições geradas por FFmpeg)';
 if(video.canPlayType('application/vnd.apple.mpegurl')){video.src=src;video.play().catch(()=>{});}
 else if(window.Hls && Hls.isSupported()){
   window.currentHls=new Hls({enableWorker:true});window.currentHls.loadSource(src);
   window.currentHls.attachMedia(video);window.currentHls.on(Hls.Events.MANIFEST_PARSED,()=>video.play().catch(()=>{}));
 } else {document.getElementById('message').textContent='Este navegador não suporta HLS.';}
}
let desiredBufferSeconds=20;
function setBuffer(){desiredBufferSeconds=Number(document.getElementById('bufferSeconds').value)||20;}
const monitoredVideo=document.getElementById('player');
setInterval(()=>{
 const buffered=monitoredVideo.buffered.length?Math.max(0,monitoredVideo.buffered.end(monitoredVideo.buffered.length-1)-monitoredVideo.currentTime):0;
 const state=monitoredVideo.paused?'pausado':(monitoredVideo.readyState<3?'carregando':'reproduzindo');
 document.getElementById('playbackStats').textContent=`Buffer: ${buffered.toFixed(1)} s • Estado: ${state} • Buffer alvo HLS: ${desiredBufferSeconds}s`;
},1000);
function playHlsP2P(name){
 const filename=decodeURIComponent(name), stem=filename.replace(/\.[^.]+$/,'');
 const master='/p2p_hls/'+encodeURIComponent('hls_'+stem+'_master.m3u8');
 const video=document.getElementById('player');
 if(window.currentHls){window.currentHls.destroy();window.currentHls=null}
 document.getElementById('playing').textContent='HLS distribuído via P2P: '+filename+' — playlists e segmentos são obtidos dos peers.';
 if(video.canPlayType('application/vnd.apple.mpegurl')){video.src=master;video.play().catch(()=>{});}
 else if(window.Hls && Hls.isSupported()){
   window.currentHls=new Hls({enableWorker:true,lowLatencyMode:false,
     maxBufferLength:desiredBufferSeconds, maxMaxBufferLength:desiredBufferSeconds*2,
     backBufferLength:Math.min(30,desiredBufferSeconds)});
   window.currentHls.loadSource(master);window.currentHls.attachMedia(video);
   window.currentHls.on(Hls.Events.MANIFEST_PARSED,()=>video.play().catch(()=>{}));
   window.currentHls.on(Hls.Events.ERROR,(event,data)=>{if(data.fatal)document.getElementById('message').textContent='Erro HLS: '+data.details;});
 } else {document.getElementById('message').textContent='Este navegador não suporta HLS.';}
}
refresh();setInterval(refresh,10000);
</script></body></html>"""

class ProgressiveStream:
    """Coordena download P2P e leitura HTTP progressiva do arquivo parcial."""
    def __init__(self, peer, filename):
        self.peer, self.filename = peer, filename
        self.path = peer.download_dir / (filename + ".part")
        self.condition = threading.Condition()
        self.completed = set()
        self.total_size = None
        self.total_chunks = None
        self.done = False
        self.error = None
        self.started = False

    def mark_chunk(self, index, block, total_size, total_chunks):
        with self.condition:
            self.total_size = total_size
            self.total_chunks = total_chunks
            self.completed.add(index)
            self.condition.notify_all()

    def start(self):
        with self.condition:
            if self.started:
                return
            self.started = True
        def run():
            try:
                self.peer.download(self.filename, on_chunk=self.mark_chunk)
                final = self.peer.download_dir / self.filename
                if final.exists():
                    self.path = final
                else:
                    self.error = "Download P2P interrompido antes da conclusão."
            except Exception as exc:
                self.error = str(exc)
            finally:
                with self.condition:
                    self.done = True
                    self.condition.notify_all()
        threading.Thread(target=run, daemon=True).start()

    def wait_for_chunk(self, index, timeout=60):
        deadline = time.monotonic() + timeout
        with self.condition:
            while index not in self.completed and not self.done:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self.condition.wait(remaining)
            return index in self.completed or self.done

class Handler(BaseHTTPRequestHandler):
    peer = None
    started_at = time.time()
    download_state = {"running": False, "message": "Aguardando."}
    state_lock = threading.Lock()
    streams = {}
    streams_lock = threading.Lock()
    p2p_resource_locks = {}
    p2p_resource_locks_guard = threading.Lock()

    @classmethod
    def get_stream(cls, peer, filename):
        with cls.streams_lock:
            state = cls.streams.get(filename)
            if state is None or (state.done and state.error):
                state = ProgressiveStream(peer, filename)
                cls.streams[filename] = state
            state.start()
            return state

    def log_message(self, fmt, *args):
        # Não registra endereços IP de clientes na saída padrão.
        print("[HTTP]", fmt % args)

    def send_json(self, obj, status=200):
        data = json.dumps(obj).encode()
        self.send_response(status); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        path=urlparse(self.path).path
        if path == "/":
            data=HTML.encode()
            self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data);return
        if path == "/api/status":
            try: status=self.peer.control("STATUS")
            except Exception: status={"active_peers":0}
            self.send_json({"peer_alias":"peer-"+str(self.peer.peer_id or "offline")[:8],
                "active_peers":status.get("active_peers",0),"local_files":self.peer.local_files(),
                "download":self.download_state,"last_metrics":getattr(self.peer,"last_download_metrics",{}),
                "uptime_seconds":round(time.time()-self.started_at,1),
                "transport":"TCP + HLS ABR" });return
        if path == "/api/catalog":
            try: items=self.peer.list_content()
            except Exception: items=[]
            result=[]
            for item in items:
                sources=len(self.peer.discover(item["name"]))
                result.append({**item,"sources":sources})
            self.send_json({"catalog":result});return
        if path.startswith("/stream/"):
            filename=Path(unquote(path[len("/stream/"):])).name
            item=next((x for x in self.peer.list_content() if x["name"]==filename),None)
            if not item:
                self.send_error(404);return
            state=self.get_stream(self.peer, filename)
            self.serve_progressive(state, int(item["size"]))
            return
        if path.startswith("/p2p_hls/"):
            # Playlist e segmentos são arquivos individuais compartilhados pelos peers.
            name=Path(unquote(path[len("/p2p_hls/"):])).name
            if not name or name in (".", ".."):
                self.send_error(400);return
            target=self.peer.shared_file(name)
            if target is None:
                with self.p2p_resource_locks_guard:
                    resource_lock=self.p2p_resource_locks.setdefault(name, threading.Lock())
                try:
                    with resource_lock:
                        target=self.peer.shared_file(name)
                        if target is None:
                            self.peer.download(name)
                            target=self.peer.shared_file(name)
                except Exception as exc:
                    self.send_error(502, explain="Falha ao obter recurso HLS dos peers: "+str(exc));return
            if target is None:
                self.send_error(404);return
            self.serve_file(target);return
        if path.startswith("/hls/"):
            relative=Path(unquote(path[len("/hls/"):]))
            base=(Path("hls").resolve())
            target=(base/relative).resolve()
            if base not in target.parents or not target.is_file():
                self.send_error(404);return
            self.serve_file(target);return
        if path.startswith("/media/"):
            name=Path(path[len("/media/"):]).name
            target=self.peer.download_dir/name
            if not target.exists(): target=self.peer.media_dir/name
            if not target.is_file(): self.send_error(404);return
            self.serve_file(target);return
        self.send_error(404)

    def serve_progressive(self, state, size):
        start, end, status = 0, size - 1, 200
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            try:
                parts = rng[6:].split("-")
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if len(parts)>1 and parts[1] else size-1
                end = min(end, size-1); status = 206
            except ValueError:
                self.send_error(416); return
        if start < 0 or end < start or start >= size:
            self.send_error(416); return
        length=end-start+1
        self.send_response(status)
        self.send_header("Content-Type", mimetypes.guess_type(state.filename)[0] or "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        if status==206:self.send_header("Content-Range",f"bytes {start}-{end}/{size}")
        self.end_headers()
        first_chunk=start // CHUNK_SIZE
        last_chunk=end // CHUNK_SIZE
        try:
            for index in range(first_chunk, last_chunk+1):
                if not state.wait_for_chunk(index, timeout=90):
                    return
                # O último bloco só é servido após o rename atômico .part -> arquivo final.
                if state.total_chunks is not None and index == state.total_chunks - 1:
                    deadline = time.monotonic() + 90
                    with state.condition:
                        while not state.done and time.monotonic() < deadline:
                            state.condition.wait(deadline - time.monotonic())
                chunk_start=index*CHUNK_SIZE
                read_start=max(start,chunk_start)-chunk_start
                read_end=min(end+1,chunk_start+CHUNK_SIZE)-chunk_start
                remaining=read_end-read_start
                with state.condition:
                    current_path=state.path
                with current_path.open("rb") as f:
                    f.seek(chunk_start+read_start)
                    while remaining>0:
                        data=f.read(min(64*1024,remaining))
                        if not data:return
                        self.wfile.write(data);remaining-=len(data)
        except (BrokenPipeError,ConnectionResetError,OSError):
            pass

    def serve_file(self, path):
        size=path.stat().st_size
        start,end=0,size-1
        rng=self.headers.get("Range")
        status=200
        if rng and rng.startswith("bytes="):
            try:
                part=rng[6:].split("-");start=int(part[0]) if part[0] else 0
                end=int(part[1]) if len(part)>1 and part[1] else size-1
                end=min(end,size-1);status=206
            except ValueError: self.send_error(416);return
        if start<0 or end<start or start>=size: self.send_error(416);return
        length=end-start+1
        ctype=mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix==".m3u8": ctype="application/vnd.apple.mpegurl"
        if path.suffix==".ts": ctype="video/mp2t"
        self.send_response(status);self.send_header("Content-Type",ctype)
        self.send_header("Accept-Ranges","bytes");self.send_header("Content-Length",str(length))
        if status==206:self.send_header("Content-Range",f"bytes {start}-{end}/{size}")
        self.end_headers()
        try:
            with path.open("rb") as f:
                f.seek(start);remaining=length
                while remaining:
                    b=f.read(min(64*1024,remaining))
                    if not b:break
                    self.wfile.write(b);remaining-=len(b)
        except (BrokenPipeError,ConnectionResetError): pass

    def do_POST(self):
        if self.path!="/api/download":self.send_error(404);return
        try: payload=json.loads(self.rfile.read(int(self.headers.get("Content-Length","0"))))
        except Exception:self.send_json({"ok":False,"message":"JSON inválido"},400);return
        filename=Path(str(payload.get("filename",""))).name
        if not filename:self.send_json({"ok":False,"message":"Nome inválido"},400);return
        with self.state_lock:
            if self.download_state["running"]:
                self.send_json({"ok":False,"message":"Já existe um download em andamento."},409);return
            self.download_state={"running":True,"message":"Download P2P iniciado."}
        def work():
            try:
                self.peer.download(filename)
                self.download_state={"running":False,"message":"Download concluído ou interrompido; confira a pasta downloads."}
            except Exception as e:self.download_state={"running":False,"message":"Falha: "+str(e)}
        threading.Thread(target=work,daemon=True).start()
        self.send_json({"ok":True,"message":"Download iniciado. A página será atualizada."},202)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--server",default="127.0.0.1");p.add_argument("--server-port",type=int,default=9000)
    p.add_argument("--listen-host",default="0.0.0.0");p.add_argument("--listen-port",type=int,default=9100)
    p.add_argument("--advertise-host",default="127.0.0.1");p.add_argument("--web-host",default="0.0.0.0");p.add_argument("--web-port",type=int,default=8080)
    p.add_argument("--media",default="media");p.add_argument("--downloads",default="downloads")
    p.add_argument("--tls",action="store_true",help="TLS nos sockets de controle e P2P")
    p.add_argument("--ca-cert",default="certs/server.crt")
    p.add_argument("--cert",default="certs/server.crt")
    p.add_argument("--key",default="certs/server.key")
    p.add_argument("--relay-host",default=None,help="Endereço do relay de privacidade")
    p.add_argument("--relay-port",type=int,default=9200)
    a=p.parse_args()
    peer=Peer(a.server,a.server_port,a.listen_host,a.listen_port,media_dir=a.media,download_dir=a.downloads,tls=a.tls,ca_cert=a.ca_cert,certfile=a.cert,keyfile=a.key,relay_host=a.relay_host,relay_port=a.relay_port)
    peer.advertise_host_arg=a.advertise_host;peer.start()
    Handler.peer=peer
    class HTTPServerV6(ThreadingHTTPServer):
        address_family = __import__("socket").AF_INET6
    ServerClass = HTTPServerV6 if ":" in a.web_host else ThreadingHTTPServer
    http=ServerClass((a.web_host,a.web_port),Handler)
    shown_host = "[::1]" if ":" in a.web_host else "127.0.0.1"
    print(f"[WEB] Abra http://{shown_host}:{a.web_port}")
    try:http.serve_forever()
    except KeyboardInterrupt:pass
    finally:http.server_close();peer.shutdown()
if __name__=="__main__":main()
