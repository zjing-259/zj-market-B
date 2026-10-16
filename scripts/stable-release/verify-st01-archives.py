"""Verify ST-01 Docker save archives and optionally load them into local Docker."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest().upper()


def verify_archive(role: str, item: dict, load: bool) -> None:
    archive = Path(item['archive'])
    if not archive.is_file() or archive.stat().st_size != item['bytes']:
        raise RuntimeError(f'{role}: archive missing or size changed')
    if sha256(archive) != item['sha256']:
        raise RuntimeError(f'{role}: archive SHA-256 changed')
    with tarfile.open(archive, 'r') as saved:
        members = {member.name for member in saved.getmembers()}
        manifest = json.load(saved.extractfile('manifest.json'))
        if len(manifest) != 1 or item['tag'] not in manifest[0]['RepoTags']:
            raise RuntimeError(f'{role}: tag/manifest mismatch')
        image = manifest[0]
        if image['Config'] not in members or any(name not in members for name in image['Layers']):
            raise RuntimeError(f'{role}: config or layer missing')
        config = saved.extractfile(image['Config']).read()
        if 'sha256:' + hashlib.sha256(config).hexdigest() != item['id']:
            raise RuntimeError(f'{role}: image ID/config digest mismatch')
    if load:
        subprocess.run(['docker', '--context', 'desktop-linux', 'image', 'load', '--input', str(archive)],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        actual = subprocess.check_output(
            ['docker', '--context', 'desktop-linux', 'image', 'inspect', '--format', '{{.Id}}', item['tag']],
            text=True).strip()
        if actual != item['id']:
            raise RuntimeError(f'{role}: loaded image ID mismatch')
    print(f"PASS {role} {item['id']} {'loaded' if load else 'archive'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('results', type=Path)
    parser.add_argument('--load', action='store_true')
    args = parser.parse_args()
    report = json.loads(args.results.read_text(encoding='utf-8-sig'))
    expected = {'mysql', 'redis', 'rocketmq', 'marketing-a', 'market-b', 'web'}
    if set(report['images']) != expected:
        raise RuntimeError('Incomplete ST-01 image set')
    for role, item in report['images'].items():
        verify_archive(role, item, args.load)


if __name__ == '__main__':
    main()
