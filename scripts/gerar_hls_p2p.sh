#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

if [[ $# -lt 1 ]]; then
    echo "Uso: $0 media/video.mp4"
    exit 1
fi

INPUT="$1"

if [[ ! -f "$INPUT" ]]; then
    echo "Arquivo não encontrado: $INPUT" >&2
    exit 1
fi

BASE="$(basename "$INPUT")"
STEM="${BASE%.*}"
OUT="hls/$STEM"
PREFIX="hls_$STEM"

"$SCRIPT_DIR/prepare_hls.sh" "$INPUT" "$OUT"

python3 "$SCRIPT_DIR/package_hls_p2p.py" \
    "$OUT" \
    --media media \
    --prefix "$PREFIX"

echo "Pronto. Aguarde o heartbeat e use o botão HLS adaptativo P2P na interface."
