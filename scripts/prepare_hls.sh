#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Uso: $0 entrada.mp4 pasta_saida"
    exit 1
fi

INPUT="$1"
OUT="$2"

command -v ffmpeg >/dev/null || {
    echo "Instale ffmpeg: sudo apt install ffmpeg"
    exit 1
}

mkdir -p "$OUT"/{360p,480p,720p}

# Verifica se o vídeo possui faixa de áudio.
HAS_AUDIO=$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$INPUT" | head -n 1)

FILTER="[0:v]split=3[v1][v2][v3];[v1]scale=w=640:h=360:force_original_aspect_ratio=decrease:force_divisible_by=2[v1out];[v2]scale=w=854:h=480:force_original_aspect_ratio=decrease:force_divisible_by=2[v2out];[v3]scale=w=1280:h=720:force_original_aspect_ratio=decrease:force_divisible_by=2[v3out]"

if [[ -n "$HAS_AUDIO" ]]; then
    echo "Áudio detectado. Gerando HLS com áudio."

    ffmpeg -y -i "$INPUT" \
        -filter_complex "$FILTER" \
        -map "[v1out]" -map 0:a:0 \
        -map "[v2out]" -map 0:a:0 \
        -map "[v3out]" -map 0:a:0 \
        -c:v libx264 \
        -b:v:0 800k -b:v:1 1400k -b:v:2 2800k \
        -c:a aac -b:a 128k \
        -f hls \
        -hls_time 4 \
        -hls_playlist_type vod \
        -hls_flags independent_segments \
        -var_stream_map "v:0,a:0 v:1,a:1 v:2,a:2" \
        -master_pl_name master.m3u8 \
        -hls_segment_filename "$OUT/%v/segment_%03d.ts" \
        "$OUT/%v/index.m3u8"

else
    echo "Vídeo sem áudio detectado. Gerando HLS somente com vídeo."

    ffmpeg -y -i "$INPUT" \
        -filter_complex "$FILTER" \
        -map "[v1out]" \
        -map "[v2out]" \
        -map "[v3out]" \
        -c:v libx264 \
        -b:v:0 800k -b:v:1 1400k -b:v:2 2800k \
        -f hls \
        -hls_time 4 \
        -hls_playlist_type vod \
        -hls_flags independent_segments \
        -var_stream_map "v:0 v:1 v:2" \
        -master_pl_name master.m3u8 \
        -hls_segment_filename "$OUT/%v/segment_%03d.ts" \
        "$OUT/%v/index.m3u8"
fi

echo "HLS adaptativo gerado em $OUT/master.m3u8"
