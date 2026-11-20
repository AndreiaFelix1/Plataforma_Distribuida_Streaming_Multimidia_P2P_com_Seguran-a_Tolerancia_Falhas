#!/usr/bin/env bash
set -euo pipefail
mkdir -p certs
if [[ -e certs/server.crt || -e certs/server.key ]]; then
  echo 'certs/server.crt ou server.key já existe; faça backup/remova antes de regenerar.' >&2
  exit 1
fi
openssl req -x509 -newkey rsa:3072 -sha256 -days 365 \
  -nodes -keyout certs/server.key -out certs/server.crt \
  -subj '/CN=StreamP2P-Lab-CA' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign,digitalSignature,keyEncipherment' \
  -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1,IP:::1'
chmod 600 certs/server.key
chmod 644 certs/server.crt
echo 'Certificado de laboratório criado em certs/. Distribua server.crt aos peers por canal confiável.'
