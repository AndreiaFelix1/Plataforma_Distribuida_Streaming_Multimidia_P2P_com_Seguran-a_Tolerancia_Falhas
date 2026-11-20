# StreamP2P Advanced v4

Plataforma acadêmica de streaming distribuído com servidor de controle, peers TCP, download progressivo, HLS adaptativo e distribuição P2P de playlists/segmentos.

## 1. Requisitos

- Python 3.9+
- FFmpeg (`sudo apt install ffmpeg`)
- OpenSSL (para o modo TLS já existente)
- Navegador moderno. Em navegadores sem HLS nativo, a interface utiliza hls.js pela CDN; é necessária conexão com a internet para carregar essa biblioteca.

## 2. Gerar o vídeo de demonstração

```bash
./baixar_video_demo.sh
```

## 3. Gerar HLS adaptativo

```bash
./prepare_hls.sh media/big_buck_bunny_480p_30s.mp4 hls/big_buck_bunny_480p_30s
```

Isso gera rendições 360p, 480p e 720p com playlists e segmentos.

## 4. Empacotar os segmentos para compartilhamento P2P

```bash
python3 package_hls_p2p.py hls/big_buck_bunny_480p_30s --media media --prefix hls_big_buck_bunny_480p_30s
```

O script achata os arquivos HLS em nomes únicos dentro de `media/`, reescrevendo as referências das playlists. Essa etapa é necessária porque o catálogo P2P atual anuncia arquivos individuais por nome. Aguarde até 10 segundos para o heartbeat atualizar a lista de arquivos do peer fornecedor.

## 5. Executar os nós

Terminal 1 — servidor de controle:

```bash
export STREAM_SECRET='use-uma-chave-aleatoria-longa'
python3 server.py --host 127.0.0.1 --port 9000
```

Terminal 2 — peer fornecedor:

```bash
export STREAM_SECRET='use-uma-chave-aleatoria-longa'
python3 webapp.py --server 127.0.0.1 --advertise-host 127.0.0.1 --listen-port 9101 --web-port 8081
```

Terminal 3 — peer consumidor:

```bash
export STREAM_SECRET='use-uma-chave-aleatoria-longa'
python3 webapp.py --server 127.0.0.1 --advertise-host 127.0.0.1 --listen-port 9102 --web-port 8082
```

Abra `http://127.0.0.1:8082` no consumidor. Clique em **HLS adaptativo P2P** no cartão do vídeo original. O player buscará a playlist master, a playlist da resolução selecionada e os segmentos por meio do endpoint `/p2p_hls/`; recursos ausentes serão obtidos de peers via TCP. O HLS.js seleciona a qualidade automaticamente conforme seu algoritmo ABR.

**Importante:** a playlist HLS gerada é associada ao vídeo original pelo prefixo `hls_<nome-sem-extensão>`. Se o nome do arquivo for diferente, ajuste `--prefix` para `hls_<nome-sem-extensão>`.

## 6. MP4 progressivo e downloads

Os botões MP4 local, Streaming P2P ao vivo e Baixar via P2P continuam disponíveis. O modo progressivo utiliza transferência em blocos e entrega os bytes ao player conforme chegam. O modo HLS distribui segmentos e permite adaptação de qualidade pelo player.

## 7. TLS

A versão anterior já contém TLS opcional nos sockets de controle e P2P. Ative-o com `--tls` no servidor e nos peers, usando o certificado confiável e os parâmetros `--ca-cert`, `--cert` e `--key`. A configuração didática anterior desabilita a verificação do hostname e compartilha material de certificado; não use essa configuração em produção. Para produção, gere certificados individuais, com SAN correspondente ao hostname/IP anunciado, habilite validação de hostname e mantenha as chaves privadas separadas.

## 8. Experimentos sugeridos

1. MP4 progressivo versus HLS P2P.
2. HLS com um peer fornecedor versus dois fornecedores.
3. Derrubar o fornecedor durante a busca de segmentos e observar a recuperação via outra fonte.
4. Aplicar `tc netem` com atraso e perda e observar mudanças de qualidade do player, latência de segmento e rebuffering.
5. Comparar HLS ABR habilitado/desabilitado (menu de qualidade do player, quando disponível).

Registre: tempo até iniciar a reprodução, tempo de download de cada segmento, throughput, número de falhas/requisições repetidas, qualidade/resolução escolhida e tempo de rebuffering. Com TCP, a perda de segmentos IP é normalmente recuperada pelo transporte; para medir perda de rede use `tc`, `ping` ou `iperf3` e diferencie essa métrica de falhas de blocos na aplicação.

### Atalho: gerar e publicar HLS P2P em um comando

Com o vídeo em `media/`, execute:

```bash
./gerar_hls_p2p.sh media/big_buck_bunny_480p_30s.mp4
```

O script executa o FFmpeg, cria as variantes e empacota playlists/segmentos com o prefixo esperado pela interface. O peer fornecedor deve estar executando para anunciar os arquivos no heartbeat.


## 9. Itens adicionais desta entrega

- **IPv6:** os sockets de controle e P2P aceitam endereços IPv6; a interface HTTP também pode escutar em IPv6 usando `--web-host ::`.
- **Multicast:** `multicast_discovery.py` oferece descoberta auxiliar em rede local IPv4 (não substitui o bootstrap).
- **Adaptação de taxa:** o modo HLS usa rendições 360p/480p/720p e seleção ABR do hls.js. O buffer pode ser ajustado na interface.
- **Monitoramento:** painel web com peers ativos, arquivos locais, estado de download, métricas de vazão/falhas e estado/buffer do player.
- **Docker/Mininet:** arquivos `Dockerfile`, `docker-compose.yml` e `mininet_topology.py` para experimentação virtualizada.
- **Especificação formal:** consulte `PROTOCOLO.md`.
- **Rastreabilidade:** consulte `MATRIZ_REQUISITOS.md`.

## 10. Testes locais automatizados

```bash
python3 -m unittest -v test_protocol.py
python3 -m py_compile protocol.py server.py peer.py webapp.py
```

Os testes automatizados verificam enquadramento de mensagens, HMAC e SHA-256. Eles não substituem os testes de integração com vários processos e máquinas.
