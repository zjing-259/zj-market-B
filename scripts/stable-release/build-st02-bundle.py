"""Build the sealed, relocatable TD-06 runtime bundle without touching containers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import ssl
import subprocess
import sys
from pathlib import Path

B = Path(__file__).resolve().parents[2]
ST00 = B / 'target/stable-isolation/st00_20261016_01/private-inventory.json'
SOURCE = B / 'target/team-discovery/td06_2_main_20261015_01'
ST01 = B / 'docs/stable-manifest.json'
RELEASE = 'td06-stable-20261016-01'
SERVICES = ('mysql', 'redis', 'namesrv', 'broker', 'marketing-a', 'market-b', 'web')


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest().upper()


def restrict_private(path: Path) -> None:
    if os.name != 'nt':
        path.chmod(0o700)
        for entry in path.rglob('*'):
            entry.chmod(0o700 if entry.is_dir() else 0o600)
        return
    account = subprocess.check_output(['whoami'], text=True).strip()
    entries = [path, *path.rglob('*')]
    subprocess.run(['icacls', str(path), '/inheritance:r', '/T', '/C'], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for entry in entries:
        command = ['icacls', str(entry), '/grant:r', account + ':F', 'SYSTEM:F', 'Administrators:F']
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build(root: Path) -> None:
    root = root.resolve()
    if root.exists():
        raise RuntimeError('Bundle already exists; choose a new batch')
    st00, stable = load(ST00), load(ST01)
    if stable['status'] != 'LOCAL_SOURCE_AND_IMAGES_ARCHIVED' or len(stable['images']) != 6:
        raise RuntimeError('ST-01 baseline missing')
    original = {mode: load(SOURCE / f'compose-{mode}.json') for mode in ('on', 'maintenance')}
    for mode, compose in original.items():
        if compose['name'] != stable['mainProject'] or set(compose['services']) != set(SERVICES) | {'mq-permissions'}:
            raise RuntimeError('Unexpected source Compose layout: ' + mode)
    private = root / 'private'
    release = root / 'releases' / RELEASE
    state = root / 'state'
    private.mkdir(parents=True)
    release.mkdir(parents=True)
    state.mkdir(parents=True)
    frozen_sources: dict[str, dict] = {}
    source_by_path = {str(Path(v['hostPath']).resolve()).lower(): v['sha256']
                      for v in st00['bindSources'].values()}

    def copy_private(value: str) -> str:
        path = Path(value).resolve()
        key = str(path).lower()
        if not path.is_file():
            raise RuntimeError('Required live file missing: ' + path.name)
        if key not in frozen_sources:
            expected = source_by_path.get(key)
            if expected and sha(path) != expected:
                raise RuntimeError('Live mount changed since ST-00: ' + path.name)
            name = f'{len(frozen_sources):03d}-{path.name}'
            destination = private / 'files' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            if sha(destination) != sha(path):
                raise RuntimeError('Copied file hash mismatch: ' + path.name)
            frozen_sources[key] = {'relativePath': 'files/' + name,
                                   'sha256': sha(destination), 'bytes': destination.stat().st_size}
        return '@private/' + frozen_sources[key]['relativePath']

    role = stable['serviceImageRoles']
    templates = {}
    for mode, compose in original.items():
        for name, service in compose['services'].items():
            service.pop('build', None)
            service['image'] = stable['images'][role[name]]['imageId']
            for mount in service.get('volumes', []):
                if mount.get('type') == 'bind':
                    mount['source'] = copy_private(mount['source'])
                    mount['read_only'] = True
                    mount['bind'] = {'create_host_path': False}
        for secret in compose['secrets'].values():
            secret['file'] = copy_private(secret['file'])
            secret['external'] = False
        for name, volume in compose['volumes'].items():
            expected = 'zj-market-b06_' + name
            if volume['name'] != expected or expected not in stable['environment']['existingVolumeNames']:
                raise RuntimeError('Volume identity changed: ' + name)
            compose['volumes'][name] = {'name': expected, 'external': True}
        for name, network in compose['networks'].items():
            expected = 'zj-market-b06_' + name
            if network['name'] != expected or expected not in stable['environment']['existingNetworkNames']:
                raise RuntimeError('Network identity changed: ' + name)
            compose['networks'][name] = {'name': expected, 'external': True}
        if any('build' in service for service in compose['services'].values()):
            raise RuntimeError('Build directive in stable Compose')
        path = release / f'compose-{mode}.template.json'
        write(path, compose)
        templates[mode] = {'file': path.relative_to(root).as_posix(), 'sha256': sha(path)}

    extras = {}
    for key, name in [('oldCa', 'web-ca.pem'), ('oldDemoAccounts', 'demo-accounts.json'),
                      ('oldSeedGoods', 'seed-goods-id.txt')]:
        dep = st00['dependencyFiles'][key]
        path = Path(dep['path'])
        if sha(path) != dep['sha256']:
            raise RuntimeError('Read-only probe material changed: ' + name)
        relative = copy_private(str(path)).removeprefix('@private/')
        extras[name] = {'relativePath': relative, 'sha256': sha(private / relative)}
    certificate = private / extras['web-ca.pem']['relativePath']
    certificate_der = ssl.PEM_cert_to_DER_cert(certificate.read_text(encoding='ascii'))
    fingerprint = 'SHA256:' + hashlib.sha256(certificate_der).hexdigest().upper()
    tools = {}
    for name, source in [('controller.py', B / 'scripts/stable-release/stable-controller.py'),
                         ('stable-probe.mjs', B / 'scripts/stable-release/stable-probe.mjs'),
                         ('stable.ps1', B / 'scripts/stable-release/stable.ps1'),
                         ('open-stable.ps1', B / 'scripts/stable-release/open-stable.ps1')]:
        target = release / name
        shutil.copyfile(source, target)
        tools[name] = sha(target)
    node = shutil.which('node')
    docker = shutil.which('docker')
    if not node or not docker:
        raise RuntimeError('Explicit Node and Docker executables are required')
    public = {
        'format': 1, 'release': RELEASE, 'project': 'zj-market-b06',
        'sourceManifestSha256': sha(ST01), 'sourceCommitA': stable['source']['a']['baselineCommit'],
        'sourceCommitB': stable['source']['b']['baselineCommit'],
        'images': {name: value['imageId'] for name, value in stable['images'].items()},
        'serviceImageRoles': role, 'volumes': stable['environment']['existingVolumeNames'],
        'networks': stable['environment']['existingNetworkNames'],
        'volumeIdentity': {value['Name']: value['CreatedAt'] for value in st00['volumeInspect']},
        'networkIdentity': {value['Name']: value['Id'] for value in st00['networkInspect']},
        'schemaFingerprint': stable['schema']['aFingerprint'],
        'flywayHistorySha256': stable['schema']['bFlywayHistorySha256'],
        'discoveryIndexColumns': stable['schema']['discoveryIndexColumns'],
        'templates': templates, 'tools': tools,
        'privateManifestSha256': None, 'webCaFingerprint': fingerprint,
        'pythonExecutable': str(Path(sys.executable).resolve()),
        'nodeExecutable': str(Path(node).resolve()),
        'dockerExecutable': str(Path(docker).resolve()),
        'edgeExecutable': 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    }
    private_manifest = {'files': list(frozen_sources.values()), 'probe': extras}
    write(private / 'files-manifest.json', private_manifest)
    public['privateManifestSha256'] = sha(private / 'files-manifest.json')
    write(release / 'release.json', public)
    restrict_private(private)
    print(json.dumps({'status': 'ST02_BUNDLE_BUILT', 'release': RELEASE,
                      'copiedPrivateFiles': len(frozen_sources), 'privateAclRestricted': True,
                      'root': str(root)}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    build(args.root)


if __name__ == '__main__':
    main()
