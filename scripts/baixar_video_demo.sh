#!/usr/bin/env bash
set -euo pipefail
mkdir -p media
URL="https://raw.githubusercontent.com/bower-media-samples/big-buck-bunny-480p-30s/master/video.mp4"
curl -L --fail --retry 3 "$URL" -o media/big_buck_bunny_480p_30s.mp4
cat > media/ATRIBUICAO.txt <<'EOF'
Big Buck Bunny (trecho de demonstração, 480p, 30 segundos)
(c) copyright 2008, Blender Foundation / www.bigbuckbunny.org
Licença: Creative Commons Attribution 3.0 (CC BY 3.0).
Fonte do arquivo de teste: bower-media-samples/big-buck-bunny-480p-30s.
EOF
echo "Vídeo baixado em media/. Confira a atribuição antes de redistribuir."
