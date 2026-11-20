#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "Inicie o servidor de controle em outro terminal:"
echo "  export STREAM_SECRET='troque-por-uma-chave-longa'"
echo "  python3 server.py --host 0.0.0.0 --port 9000"
echo
echo "Depois inicie cada peer em um terminal separado, ajustando as portas:"
echo "  export STREAM_SECRET='troque-por-uma-chave-longa'"
echo "  python3 webapp.py --server 127.0.0.1 --advertise-host 127.0.0.1 --listen-port 9101 --web-port 8081"
echo "  python3 webapp.py --server 127.0.0.1 --advertise-host 127.0.0.1 --listen-port 9102 --web-port 8082"
