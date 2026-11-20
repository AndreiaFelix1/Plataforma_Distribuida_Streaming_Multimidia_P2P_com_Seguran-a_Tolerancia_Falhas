#!/usr/bin/env python3
"""Achata playlists e segmentos HLS em arquivos individuais compartilháveis via P2P."""
import argparse
import re
import shutil
from pathlib import Path

URI_ATTR = re.compile(r'URI="([^"]+)"')

def package(source: Path, media: Path, prefix: str):
    source = source.resolve(); media.mkdir(parents=True, exist_ok=True)
    if not (source / 'master.m3u8').is_file():
        raise SystemExit(f"Playlist não encontrada: {source / 'master.m3u8'}")
    mapping = {}
    for item in source.rglob('*'):
        if item.is_file() and item.suffix.lower() in {'.m3u8', '.ts', '.m4s', '.mp4', '.key'}:
            rel = item.relative_to(source).as_posix()
            # Nomes determinísticos e sem diretórios: compatíveis com o catálogo atual.
            safe = re.sub(r'[^A-Za-z0-9_.-]+', '_', rel.replace('/', '__'))
            mapping[rel] = f'{prefix}_{safe}'
    for rel, dest_name in mapping.items():
        src = source / rel
        if src.suffix.lower() != '.m3u8':
            shutil.copy2(src, media / dest_name)
            continue
        lines = src.read_text(encoding='utf-8').splitlines()
        rewritten = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                def attr_replace(match):
                    uri = match.group(1)
                    mapped = mapping.get((Path(rel).parent / uri).as_posix())
                    return f'URI="{mapped}"' if mapped else match.group(0)
                rewritten.append(URI_ATTR.sub(attr_replace, line))
            else:
                mapped = mapping.get((Path(rel).parent / stripped).as_posix())
                rewritten.append(mapped or stripped)
        (media / dest_name).write_text('\n'.join(rewritten) + '\n', encoding='utf-8')
    master = mapping['master.m3u8']
    print(f"Pacote HLS P2P criado em {media.resolve()}")
    print(f"Playlist master: {master}")
    print(f"Arquivos compartilháveis: {len(mapping)}")
    print("Aguarde o heartbeat dos peers (até 10 segundos) para atualizar o catálogo.")

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('hls_directory', help='Pasta gerada por prepare_hls.sh')
    p.add_argument('--media', default='media')
    p.add_argument('--prefix', default='hls_video')
    a=p.parse_args()
    package(Path(a.hls_directory),Path(a.media),a.prefix)
