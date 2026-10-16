"""Create or check the public ST-01 source/image archive manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

B = Path(__file__).resolve().parents[2]
A = Path('D:/Java/group-buy-market')
TAG = 'stable-td06-20261016-01'
OUT = B / 'docs/stable-manifest.json'
ARCHIVES = B / 'target/stable-isolation/st01_20261016_01/archive-results.json'


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest().upper()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def source(repo: Path, names: dict[str, str]) -> dict:
    if git(repo, 'cat-file', '-t', 'refs/tags/' + TAG) != 'tag':
        raise RuntimeError('ST-01 tag must be annotated')
    commit = git(repo, 'rev-parse', TAG + '^{}')
    if subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', commit, 'HEAD'],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        raise RuntimeError('Baseline tag is not an ancestor of current branch')
    same = converted = 0
    for name, expected in names.items():
        working = (repo / name).read_bytes()
        if hashlib.sha256(working).hexdigest().upper() != expected:
            raise RuntimeError('TD-06 worktree source drift: ' + name)
        committed = subprocess.check_output(['git', '-C', str(repo), 'show', TAG + ':' + name])
        if committed == working:
            same += 1
        elif committed.replace(b'\n', b'\r\n') == working:
            converted += 1
        else:
            raise RuntimeError('Git source differs beyond CRLF conversion: ' + name)
    return {
        'branch': git(repo, 'branch', '--show-current'),
        'baselineCommit': commit,
        'annotatedTag': TAG,
        'tagObject': git(repo, 'rev-parse', 'refs/tags/' + TAG),
        'frozenFileCount': len(names),
        'gitBlobExactByteCount': same,
        'gitBlobLfToWorktreeCrlfCount': converted,
    }


def collect() -> dict:
    td06 = load(B / 'docs/team-discovery-td06-release.json')
    lock = load(B / 'docs/team-discovery-td06-source-lock.json')
    st00 = load(B / 'docs/tests/st00-acceptance.json')
    archives = load(ARCHIVES)
    if sha(B / 'docs/team-discovery-td06-source-lock.json') != td06['source']['sourceLockSha256']:
        raise RuntimeError('Historical source lock changed')
    a = source(A, lock['a'])
    b = source(B, lock['b'])
    if a['baselineCommit'] == td06['source']['a']['head'] or b['baselineCommit'] == td06['source']['b']['head']:
        raise RuntimeError('Source baseline commit was not created')
    ids = st00['runtime']['images']
    expected = {'mysql': ids['mysql'], 'redis': ids['redis'], 'rocketmq': ids['broker'],
                'marketing-a': ids['marketing-a'], 'market-b': ids['market-b'], 'web': ids['web']}
    if ids['broker'] != ids['namesrv'] or ids['broker'] != st00['runtime']['stoppedAuxiliary']['imageId']:
        raise RuntimeError('RocketMQ auxiliary image mismatch')
    if set(archives['images']) != set(expected):
        raise RuntimeError('Six unique image archives required')
    images = {}
    for role, item in archives['images'].items():
        path = Path(item['archive'])
        if item['id'] != expected[role] or item['sha256'] != sha(path) or item['bytes'] != path.stat().st_size:
            raise RuntimeError('Image archive changed: ' + role)
        images[role] = {
            'imageId': item['id'], 'stableTag': item['tag'],
            'archiveRelativePath': path.relative_to(B).as_posix(),
            'archiveSha256': item['sha256'], 'archiveBytes': item['bytes'],
            'loadVerifiedOnCurrentDockerEngine': True,
        }
    if any(images[role]['imageId'] != td06['images'][service] for role, service in
           [('marketing-a', 'marketing-a'), ('market-b', 'market-b'), ('web', 'web')]):
        raise RuntimeError('Application images differ from TD-06 archive')
    return {
        'stage': 'ST-01', 'status': 'LOCAL_SOURCE_AND_IMAGES_ARCHIVED',
        'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
        'mainProject': 'zj-market-b06', 'mainOrigin': 'https://zj-market.test',
        'source': {
            'a': a, 'b': b,
            'historicalFrozenLockSha256': td06['source']['sourceLockSha256'],
            'aFrozenSourceDigest': td06['source']['aSourceDigest'],
            'bFrozenSourceDigest': td06['source']['bSourceDigest'],
            'relationToRunningImages': 'TD-05/TD-06 build evidence ties frozen worktree bytes and JAR/web outputs to the running image IDs; commits were created later and are not claimed as image build inputs',
            'gitEolNote': '527 Git blobs normalize LF; their Windows worktree bytes exactly equal the frozen source lock after LF-to-CRLF conversion',
        },
        'images': images,
        'serviceImageRoles': {'mysql': 'mysql', 'redis': 'redis', 'namesrv': 'rocketmq',
                              'broker': 'rocketmq', 'mq-permissions': 'rocketmq',
                              'marketing-a': 'marketing-a', 'market-b': 'market-b', 'web': 'web'},
        'buildEvidence': {
            'td05BuildManifestSha256': td06['privateEvidenceSha256']['td05BuildManifest'],
            'aAppJarSha256': td06['build']['aAppJarSha256'],
            'bAppJarSha256': td06['build']['bAppJarSha256'],
            'mainWebBuildFileSha256': td06['build']['mainWebBuild'],
            'historicalTd06ReleaseSha256': sha(B / 'docs/team-discovery-td06-release.json'),
        },
        'contract': td06['contract'], 'schema': td06['schema'],
        'publicConfigTemplatesSha256': td06['configTemplatesSha256'],
        'privateLiveMountInventory': {
            'path': 'target/stable-isolation/st00_20261016_01/private-inventory.json',
            'sha256': st00['privateInventorySha256'],
            'note': 'Ignored local inventory contains live bind source paths and hashes; secret contents and hashes are not published here',
        },
        'environment': {
            'hostTools': st00['hostTools'], 'existingVolumeNames': st00['runtime']['volumes'],
            'existingNetworkNames': st00['runtime']['networks'],
            'historicalWorktreeDependencyRemains': True,
            'windowsDockerDesktopOnlyValidated': True,
        },
        'historicalEvidence': {
            'td06Release': 'docs/team-discovery-td06-release.json',
            'td06SourceLock': 'docs/team-discovery-td06-source-lock.json',
            'st00Acceptance': 'docs/tests/st00-acceptance.json',
            'st00AcceptanceSha256': sha(B / 'docs/tests/st00-acceptance.json'),
        },
        'scope': {'gitPushed': False, 'registryPublished': False, 'deploymentChanged': False,
                  'containersOrVolumesRecreated': False, 'imagesArchivedLocally': True,
                  'independentStableDeploymentReady': False},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('write', 'check'))
    mode = parser.parse_args().mode
    report = collect()
    if mode == 'write':
        if OUT.exists():
            raise RuntimeError('Manifest already exists; do not overwrite')
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    else:
        saved = load(OUT)
        report['generatedAtUtc'] = saved['generatedAtUtc']
        if report != saved:
            raise RuntimeError('ST-01 manifest drift')
    print('PASS ST-01 manifest ' + mode)


if __name__ == '__main__':
    main()
