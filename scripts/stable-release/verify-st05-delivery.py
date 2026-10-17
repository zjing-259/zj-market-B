"""Verify a sealed ST-05 local delivery package without touching live volumes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest().upper()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def check_inventory(root: Path, records: list[dict], extra: set[str] | None = None) -> None:
    expected = {item['path'] for item in records} | (extra or set())
    actual = set()
    for item in root.rglob('*'):
        if item.is_symlink():
            raise RuntimeError('Symlink in package: ' + str(item))
        if item.is_file():
            actual.add(item.relative_to(root).as_posix())
    if actual != expected:
        raise RuntimeError('Package file set differs from sealed inventory')
    for item in records:
        path = root / item['path']
        if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            raise RuntimeError('Package file drift: ' + item['path'])


def verify(root: Path) -> dict:
    root = root.resolve(strict=True)
    public = read(root / 'public-manifest.json')
    private = read(root / 'private/private-manifest.json')
    complete = read(root / 'COMPLETE.json')
    if public['stage'] != 'ST-05' or public['status'] != 'LOCAL_DELIVERY_COMPLETE' or private['stage'] != 'ST-05':
        raise RuntimeError('Wrong delivery stage or status')
    if digest(root / 'public-manifest.json') != complete['publicManifestSha256']:
        raise RuntimeError('Public manifest drift')
    private_hash = digest(root / 'private/private-manifest.json')
    if private_hash != complete['privateManifestSha256'] or private_hash != public['privateManifestSha256']:
        raise RuntimeError('Private manifest drift')
    check_inventory(root / 'public', public['publicFiles'])
    check_inventory(root / 'private', private['files'], {'private-manifest.json'})
    if len(private['files']) != public['privateFileCount'] or sum(f['bytes'] for f in private['files']) != public['privateTotalBytes']:
        raise RuntimeError('Private inventory aggregate drift')
    if {p.name for p in root.iterdir()} != {'public', 'private', 'public-manifest.json', 'COMPLETE.json'}:
        raise RuntimeError('Unexpected top-level delivery item')
    stable = root / 'private/stable-runtime'
    source_manifest = read(root / 'public/docs/stable-manifest.json')
    release = read(stable / 'releases/td06-stable-20261016-01/release.json')
    for role, item in public['stableImages'].items():
        source = source_manifest['images'][role]
        archive = stable / 'images' / (role + '.tar')
        if item != {'imageId': source['imageId'], 'sha256': source['archiveSha256'], 'bytes': source['archiveBytes']}:
            raise RuntimeError('Stable image metadata drift: ' + role)
        if release['images'][role] != item['imageId'] or digest(archive) != item['sha256']:
            raise RuntimeError('Stable image payload drift: ' + role)
    ux = public['uxWebImage']
    if digest(root / 'private/ux-images/web-st04-20261017-02.tar') != ux['sha256']:
        raise RuntimeError('UX Web image archive drift')
    static = subprocess.check_output([sys.executable,
        str(Path(__file__).with_name('verify-st02-bundle.py')), str(stable)],
        text=True, encoding='utf-8')
    if read_json(static)['status'] != 'ST02_BUNDLE_STATIC_PASS':
        raise RuntimeError('Stable independent bundle static verification failed')
    if os.name == 'nt':
        acl = subprocess.check_output(['icacls', str(root / 'private')], text=True, encoding='utf-8')
        if 'BUILTIN\\Users:' in acl or 'Everyone:' in acl or 'Authenticated Users:' in acl:
            raise RuntimeError('Private directory has broad direct ACL')
    return {'status': 'ST05_DELIVERY_VERIFIED', 'publicFiles': len(public['publicFiles']),
            'privateFiles': len(private['files']), 'stableImages': len(public['stableImages']),
            'uxWebImage': ux['imageId'], 'stableBundleStatic': True,
            'liveVolumesTouched': False}


def read_json(value: str) -> dict:
    return json.loads(value)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    print(json.dumps(verify(parser.parse_args().root), ensure_ascii=False))
