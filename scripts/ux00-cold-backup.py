"""Seal stopped UX volumes before a Web image change; never restore or alter volumes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'zj-market-ux'
SERVICES = ('mysql', 'redis', 'namesrv', 'broker', 'marketing-a', 'market-b', 'web')
VOLUMES = ('mysql-data', 'redis-data', 'namesrv-logs', 'broker-logs', 'broker-store')
DOCKER = ('docker', '--context', 'desktop-linux')


def call(*args: str) -> str:
    return subprocess.check_output([str(a) for a in args], text=True, encoding='utf-8').strip()


def sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest().upper()


def save(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def protect(path: Path) -> None:
    if os.name == 'nt':
        account = call('whoami')
        subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r',
                        account + ':F', 'SYSTEM:F', 'Administrators:F'],
                       check=True, capture_output=True)
    else:
        path.chmod(0o700)


def stopped_source() -> dict:
    state = json.loads((ROOT / '.local/b06/control/state.json').read_text(encoding='utf-8'))
    if state.get('project') != PROJECT or state.get('phase') != 'STOPPED':
        raise RuntimeError('UX must be stopped by its own controller first')
    for service in SERVICES:
        row = json.loads(call(*DOCKER, 'inspect', f'{PROJECT}-{service}-1'))[0]
        labels = row['Config']['Labels']
        if labels.get('com.docker.compose.project') != PROJECT or row['State']['Running']:
            raise RuntimeError('UX container ownership or stopped state mismatch: ' + service)
    volumes = {}
    for name in VOLUMES:
        full = f'{PROJECT}_{name}'
        row = json.loads(call(*DOCKER, 'volume', 'inspect', full))[0]
        labels = row['Labels']
        if labels.get('com.docker.compose.project') != PROJECT or labels.get('com.docker.compose.volume') != name:
            raise RuntimeError('UX volume ownership mismatch: ' + name)
        volumes[name] = full
    return {'state': state, 'volumes': volumes}


def inventory(base: Path) -> list[dict]:
    return [{'path': file.relative_to(base).as_posix(), 'bytes': file.stat().st_size,
             'sha256': sha(file)} for file in sorted(base.rglob('*')) if file.is_file()]


def backup(batch: str) -> None:
    if not re.fullmatch(r'ux00_\d{8}_\d{2}', batch):
        raise RuntimeError('Use a unique ux00_YYYYMMDD_NN batch')
    target = ROOT / '.local/ux00/backups' / batch
    if target.exists():
        raise RuntimeError('Backup target already exists')
    source = stopped_source()
    target.mkdir(parents=True)
    protect(target)
    private = target / 'private'
    private.mkdir()
    protect(private)
    for name in ('runtime', 'control'):
        if name == 'runtime':
            shutil.copytree(ROOT / '.local/b06/runtime', private / name)
        else:
            for file in ('state.json', 'deployment.properties', 'demo-accounts.json',
                         'capabilities.properties', 'capabilities.yml', 'seed-goods-id.txt'):
                source_file = ROOT / '.local/b06/control' / file
                destination = private / name / file
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source_file, destination)
    shutil.copyfile(ROOT / '.local/b06/build/release.env', private / 'release.env')
    image = json.loads((ROOT / 'deploy/b06/images.lock.json').read_text(encoding='utf-8'))['redis']
    for name, full in source['volumes'].items():
        archive = private / (name + '.tar')
        with archive.open('wb') as output:
            process = subprocess.run([*DOCKER, 'run', '--rm', '--network', 'none',
                                      '--mount', f'type=volume,src={full},dst=/source,readonly',
                                      '--entrypoint', 'tar', image, '-C', '/source', '-cf', '-', '.'],
                                     stdout=output, stderr=subprocess.PIPE)
        if process.returncode:
            raise RuntimeError('UX volume archive failed: ' + name)
        print('UX volume archived: ' + name, flush=True)
    manifest = {'stage': 'UX-00', 'batch': batch,
                'consistentPointUtc': datetime.now(timezone.utc).isoformat(),
                'project': PROJECT, 'volumes': source['volumes'],
                'stateAtStop': source['state']['phase'], 'files': inventory(private),
                'restoreOverLiveVolumes': False}
    save(target / 'manifest.json', manifest)
    save(target / 'COMPLETE.json', {'manifestSha256': sha(target / 'manifest.json')})
    verify(batch)
    print('UX00_COLD_BACKUP_COMPLETE ' + str(target), flush=True)


def verify(batch: str) -> None:
    target = ROOT / '.local/ux00/backups' / batch
    manifest = json.loads((target / 'manifest.json').read_text(encoding='utf-8'))
    complete = json.loads((target / 'COMPLETE.json').read_text(encoding='utf-8'))
    if manifest.get('project') != PROJECT or manifest.get('stateAtStop') != 'STOPPED' or \
       sha(target / 'manifest.json') != complete['manifestSha256']:
        raise RuntimeError('UX backup manifest drift')
    files = inventory(target / 'private')
    if files != manifest['files']:
        raise RuntimeError('UX backup payload drift')
    print('UX00_COLD_BACKUP_VERIFIED files=' + str(len(files)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('backup', 'verify'))
    parser.add_argument('--batch', required=True)
    args = parser.parse_args()
    {'backup': backup, 'verify': verify}[args.action](args.batch)
