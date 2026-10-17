"""Seal a local ST-05 delivery snapshot without mutating either running stack."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

B = Path(__file__).resolve().parents[2]
A = Path('D:/Java/group-buy-market')
UX = Path('D:/Java/zj-market-ux')
STABLE = Path('D:/Java/zj-market-stable')
BATCH = 'st05_20261017_02'
UX_WEB_TAG = 'zj-market-ux/web:st04-20261017-02'


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run(*args: str) -> str:
    return subprocess.check_output([str(arg) for arg in args], text=True, encoding='utf-8').strip()


def copy(source: Path, target: Path) -> None:
    if not source.is_file() or source.is_symlink() or target.exists():
        raise RuntimeError('Invalid or duplicate delivery input: ' + str(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def restricted(path: Path) -> None:
    if os.name != 'nt':
        path.chmod(0o700)
        return
    account = run('whoami')
    subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r',
                    account + ':F', 'SYSTEM:F', 'Administrators:F'],
                   check=True, capture_output=True)


def inventory(base: Path) -> list[dict]:
    result = []
    for file in sorted(base.rglob('*')):
        if file.is_symlink():
            raise RuntimeError('Symlink in delivery: ' + str(file))
        if file.is_file():
            result.append({'path': file.relative_to(base).as_posix(),
                           'sha256': sha(file), 'bytes': file.stat().st_size})
    return result


def build(root: Path) -> None:
    root = root.resolve()
    allowed = (B / 'target/stable-isolation').resolve()
    if root.parent != allowed or root.name != BATCH or root.exists():
        raise RuntimeError('Use a new, exact ST-05 target inside the ignored B target directory')
    release = load(STABLE / 'releases/td06-stable-20261016-01/release.json')
    stable_manifest = load(B / 'docs/stable-manifest.json')
    if release['sourceCommitA'] != stable_manifest['source']['a']['baselineCommit'] or \
       release['sourceCommitB'] != stable_manifest['source']['b']['baselineCommit']:
        raise RuntimeError('ST-01 source identity drift')
    ux_image = load_text_json(run('docker', '--context', 'desktop-linux',
                                  'image', 'inspect', UX_WEB_TAG))[0]['Id']
    if ux_image != 'sha256:449d818ce60072922cd4b41dc0d5011bdcd5b9cee58ba84d5d23e9d2abb914bb':
        raise RuntimeError('UX Web image ID changed')

    root.mkdir(parents=True)
    public = root / 'public'
    private = root / 'private'
    public.mkdir()
    private.mkdir()
    restricted(private)
    print('ST05 package directories created; private ACL restricted', flush=True)

    public_files = [
        (B / 'deploy/stable/README.md', 'deploy/stable/README.md'),
        (B / 'deploy/ux/README.md', 'deploy/ux/README.md'),
        (B / 'deploy/st05/README.md', 'deploy/st05/README.md'),
        (B / 'docs/stable-manifest.json', 'docs/stable-manifest.json'),
        (B / 'docs/stable-release-worktree-isolation-plan.md', 'docs/stable-release-worktree-isolation-plan.md'),
        (B / 'docs/tests/st03-acceptance.json', 'docs/tests/st03-acceptance.json'),
        (B / 'docs/tests/st04-acceptance.json', 'docs/tests/st04-acceptance.json'),
        (B / 'docs/tests/verify-st04-isolation.py', 'docs/tests/verify-st04-isolation.py'),
        (B / 'scripts/st04-prepare-ux.py', 'scripts/st04-prepare-ux.py'),
        (B / 'scripts/st04-fix-ux-logging.py', 'scripts/st04-fix-ux-logging.py'),
        (B / 'scripts/st04-ux-indexes.py', 'scripts/st04-ux-indexes.py'),
        (B / 'scripts/stable-release/build-st05-delivery.py', 'scripts/stable-release/build-st05-delivery.py'),
        (B / 'scripts/stable-release/verify-st05-delivery.py', 'scripts/stable-release/verify-st05-delivery.py'),
        (UX / 'deploy/b06/compose.yml', 'ux/deploy/b06/compose.yml'),
        (UX / 'deploy/b06/config/b.properties', 'ux/deploy/b06/config/b.properties'),
        (UX / 'deploy/b06/nginx.conf', 'ux/deploy/b06/nginx.conf'),
    ]
    for source, relative in public_files:
        copy(source, public / relative)
    print(f'ST05 public files copied: {len(public_files)}', flush=True)

    runtime = private / 'stable-runtime'
    for source in sorted((STABLE / 'releases/td06-stable-20261016-01').rglob('*')):
        if source.is_file():
            copy(source, runtime / source.relative_to(STABLE))
    copy(STABLE / 'scripts/stable.ps1', runtime / 'scripts/stable.ps1')
    for source in sorted((STABLE / 'private').rglob('*')):
        if source.is_file():
            copy(source, runtime / source.relative_to(STABLE))
    print('ST05 stable fixed release and private inputs copied', flush=True)

    images = {}
    for role, item in stable_manifest['images'].items():
        source = STABLE / 'images' / (role + '.tar')
        if source.stat().st_size != item['archiveBytes'] or sha(source) != item['archiveSha256']:
            raise RuntimeError('Stable image archive drift: ' + role)
        destination = runtime / 'images' / source.name
        copy(source, destination)
        if sha(destination) != item['archiveSha256']:
            raise RuntimeError('Copied stable image archive drift: ' + role)
        images[role] = {'imageId': item['imageId'], 'sha256': item['archiveSha256'],
                        'bytes': item['archiveBytes']}
        print('ST05 stable image verified: ' + role, flush=True)

    # UX credentials are private local continuity material, not a data-volume backup.
    ux_materials = private / 'ux-materials'
    for source in sorted((UX / '.local/b06/runtime').rglob('*')):
        if source.is_file():
            copy(source, ux_materials / source.relative_to(UX / '.local/b06'))
    for name in ('capabilities.properties', 'capabilities.yml', 'demo-accounts.json',
                 'deployment.properties', 'seed-goods-id.txt', 'state.json'):
        copy(UX / '.local/b06/control' / name, ux_materials / 'control' / name)
    copy(UX / '.local/b06/build/release.env', ux_materials / 'build/release.env')
    print('ST05 UX private continuity inputs copied', flush=True)

    ux_archive = private / 'ux-images/web-st04-20261017-02.tar'
    ux_archive.parent.mkdir(parents=True)
    subprocess.run(['docker', '--context', 'desktop-linux', 'save', '-o',
                    str(ux_archive), UX_WEB_TAG], check=True, capture_output=True)
    ux_archive_hash = sha(ux_archive)
    print('ST05 UX Web image archived', flush=True)

    backup = STABLE / 'backups/st03_20261016_04'
    backup_manifest = load(backup / 'manifest.json')
    if sha(backup / 'manifest.json') != load(backup / 'COMPLETE.json')['manifestSha256']:
        raise RuntimeError('ST-03 backup manifest drift')
    for name, item in backup_manifest['files'].items():
        if (backup / name).stat().st_size != item['bytes'] or sha(backup / name) != item['sha256']:
            raise RuntimeError('ST-03 backup archive drift: ' + name)
    print('ST05 historical ST-03 backup bytes reverified (not copied)', flush=True)

    private_manifest = {'stage': 'ST-05', 'files': inventory(private)}
    save(private / 'private-manifest.json', private_manifest)
    restricted(private)
    public_manifest = {
        'stage': 'ST-05', 'status': 'LOCAL_DELIVERY_COMPLETE',
        'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
        'stableRelease': release['release'], 'stableRoot': str(STABLE).replace('\\', '/'),
        'uxRoot': str(UX).replace('\\', '/'),
        'sourceCommits': {'aStable': release['sourceCommitA'], 'bStable': release['sourceCommitB'],
                          'bSt04': run('git', '-C', str(B), 'rev-parse', 'HEAD'),
                          'bUx': run('git', '-C', str(UX), 'rev-parse', 'HEAD')},
        'publicFiles': inventory(public),
        'privateFileCount': len(private_manifest['files']),
        'privateTotalBytes': sum(item['bytes'] for item in private_manifest['files']),
        'privateManifestSha256': sha(private / 'private-manifest.json'),
        'stableImages': images,
        'uxWebImage': {'imageId': ux_image, 'tag': UX_WEB_TAG,
                       'sha256': ux_archive_hash, 'bytes': ux_archive.stat().st_size},
        'historicalBackup': {'batch': backup_manifest['batch'],
                             'manifestSha256': sha(backup / 'manifest.json'),
                             'allSevenFilesReverified': True,
                             'currentAfterSt03Transactions': False,
                             'includedInPackage': False},
        'privateFilesPublishedToGit': False, 'offHostCopyPerformed': False,
    }
    save(root / 'public-manifest.json', public_manifest)
    save(root / 'COMPLETE.json', {'publicManifestSha256': sha(root / 'public-manifest.json'),
                                  'privateManifestSha256': sha(private / 'private-manifest.json')})
    print('ST05 delivery complete: ' + str(root), flush=True)


def load_text_json(value: str):
    return json.loads(value)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    build(parser.parse_args().root)
