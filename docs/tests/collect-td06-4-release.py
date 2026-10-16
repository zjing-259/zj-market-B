"""Freeze and verify the local TD-06 delivery without exposing private runtime data."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

B = Path(__file__).resolve().parents[2]
A = Path('D:/Java/group-buy-market')
OLD = Path('D:/Java/zj-market-b-06')
TD05 = B / 'target/team-discovery/td05_20261015_01'
TD062 = B / 'target/team-discovery/td06_2_main_20261015_01'
TD063 = B / 'target/team-discovery/td06_3_main_20261016_01'
BACKUP = OLD / '.local/b06/backups/b066-td062-20261015-03'
LOCK = B / 'docs/team-discovery-td06-source-lock.json'
OUT = B / 'docs/team-discovery-td06-release.json'


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError('Missing release artifact: ' + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(data) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest().upper()


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def head(repo: Path) -> dict:
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
    return {'branch': git('branch', '--show-current'), 'head': git('rev-parse', 'HEAD'),
            'worktreeClean': not bool(git('status', '--porcelain'))}


def paths(base: Path, names: list[str]) -> dict[str, str]:
    return {name: sha(base / name) for name in names}


def public_file_audit(repo: Path) -> dict:
    changed = set()
    untracked = set()
    for arguments, target in [(['diff', '--name-only', '-z'], changed),
                              (['diff', '--cached', '--name-only', '-z'], changed),
                              (['ls-files', '--others', '--exclude-standard', '-z'], untracked)]:
        for raw in subprocess.check_output(['git', '-C', str(repo), *arguments]).split(b'\0'):
            if raw:
                target.add(raw.decode('utf-8'))
    names = changed | untracked
    generated = {'docs/team-discovery-td06-source-lock.json', 'docs/team-discovery-td06-release.json'}
    names -= generated
    untracked -= generated
    bad_names = re.compile(r'(^|/)(\.local|target|node_modules|__pycache__)(/|$)|\.(pem|key|p12|pfx|jks|keystore|har|log|dump|pyc)$|(^|/)(demo-accounts|credentials|secrets)\.json$', re.I)
    mark = '-----'
    exposed = re.compile(mark + r'BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY' + mark + '|' +
                         mark + r'BEGIN CERTIFICATE' + mark +
                         r'|AKIA[0-9A-Z]{16}|Bearer [A-Za-z0-9._~-]{40,}|eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}')
    text_suffixes = {'.md', '.json', '.py', '.ps1', '.js', '.mjs', '.ts', '.vue', '.java',
                     '.xml', '.properties', '.yml', '.yaml', '.sql', '.txt', '.conf', '.dockerfile'}
    for name in names:
        file = repo / name
        if bad_names.search(name.replace('\\', '/')) or file.is_symlink():
            raise RuntimeError('Private or generated file in public worktree: ' + name)
        if not file.is_file():
            continue
        if file.suffix.lower() in text_suffixes or file.name.startswith('.'):
            if file.stat().st_size > 4_000_000:
                raise RuntimeError('Oversized changed public file: ' + name)
            value = file.read_text(encoding='utf-8-sig', errors='replace')
            if exposed.search(value):
                raise RuntimeError('Potential secret or certificate in public file: ' + name)
    return {'changedOrUntrackedCount': len(names), 'untrackedCount': len(untracked),
            'privateKeyCertificateTokenOrBackupFindings': 0}


def collect():
    td05_release = load(B / 'docs/team-discovery-td05-release.json')
    td062 = load(B / 'docs/tests/td06-2-acceptance.json')
    td063 = load(B / 'docs/tests/td06-3-acceptance.json')
    release = load(TD062 / 'release.json')
    lock = load(B / 'docs/team-discovery-contract-lock.json')
    prior = module('td05_collect', B / 'docs/tests/collect-td05-release.py')
    deployment = module('td06_deployment', B / 'scripts/td06-main-release.py')
    if td05_release['status'] != 'LOCAL_WINDOWS_CANDIDATE_VERIFIED' or td062['status'] != 'PASSED_MAIN_443_RELEASE' or td063['status'] != 'PASSED_MAIN443_CONSERVATION':
        raise RuntimeError('Prerequisite acceptance missing')
    if release['status'] != 'RESTARTED_443':
        raise RuntimeError('Main release not complete')
    a_files = load(TD05 / 'a-source-hashes.json')
    if any(sha(A / name) != expected for name, expected in a_files.items()):
        raise RuntimeError('Frozen A source drift')
    if digest(a_files) != td05_release['aFrozenSourceSha256']:
        raise RuntimeError('A source lock drift')
    b_files = prior.source_hashes(B)
    harness_names = [
        '.gitignore',
        'scripts/open-team-discovery-browser.ps1', 'scripts/td06-environment.py',
        'scripts/td06-main-release.py', 'docs/tests/td06-main-gate.mjs',
        'docs/tests/td06-3-real-browser.mjs', 'docs/tests/td06-3-discovery-readonly.mjs',
        'docs/tests/run-td06-3-joint.py', 'docs/tests/collect-td06-3-joint.py',
        'docs/tests/collect-td06-3-final.py', 'docs/tests/collect-td06-4-release.py',
    ]
    sources = {'a': a_files, 'b': b_files, 'releaseHarness': paths(B, harness_names)}
    if sha(TD05 / 'a-source/group-buy-market-contract/target/group-buy-market-contract-1.1.0-td.1.jar') != lock['sha256']:
        raise RuntimeError('Frozen contract jar drift')
    if sha(B / 'docs/team-discovery-contract.json') != td05_release['contract']['apiJsonSha256']:
        raise RuntimeError('Frozen contract JSON drift')
    jar_a = sha(TD05 / 'build/a/app.jar')
    jar_b = sha(TD05 / 'build/b/app.jar')
    if jar_a != td05_release['buildContexts']['a']['app.jar'] or jar_b != td05_release['buildContexts']['b']['app.jar']:
        raise RuntimeError('Published image build jar drift')
    web = {path.relative_to(TD062 / 'build/web').as_posix(): sha(path)
           for path in sorted((TD062 / 'build/web').rglob('*')) if path.is_file()}
    if not {'Dockerfile', 'nginx.conf', 'dist/index.html'}.issubset(web):
        raise RuntimeError('Main web build incomplete')
    expected_images = {'marketing-a': release['images']['a'], 'market-b': release['images']['b'],
                       'web': release['images']['web']}
    running = deployment.containers(expected_images)
    deployment.verify_schema(True)
    deployment.public_gate('on')
    for name, image in expected_images.items():
        value = json.loads(deployment.run(deployment.DOCKER + ['image', 'inspect', image]))[0]
        if value['Id'] != image or value['Architecture'] != 'amd64':
            raise RuntimeError('Main image local ID/architecture drift: ' + name)
    templates = ['deploy/b06/compose.yml', 'deploy/b06/images/java.Dockerfile',
                 'deploy/b06/images/web.Dockerfile', 'deploy/b06/nginx.conf',
                 'deploy/b06/config/a.properties', 'deploy/b06/config/b.properties',
                 'deploy/b06/config/admission-open.conf', 'deploy/b06/config/admission-maintenance.conf']
    template_hashes = paths(B, templates)
    private_artifacts = {
        'td05BuildManifest': TD05 / 'release-manifest.json',
        'td062ReleaseEvents': TD062 / 'release.json',
        'td062MainComposeOn': TD062 / 'compose-on.json',
        'td062BackupManifest': BACKUP / 'manifest.json',
        'td062BackupSeal': BACKUP / 'COMPLETE.json',
        'td063Before': TD063 / 'before.json',
        'td063Browser': TD063 / 'browser/browser-report.json',
        'td063Accounting': TD063 / 'browser/accounting-report.json',
        'td063After': TD063 / 'after.json',
        'td063TerminalDiscovery': TD063 / 'browser/discovery-readonly.json',
    }
    evidence = {key: sha(path) for key, path in private_artifacts.items()}
    previous = td063['privateEvidenceSha256']
    for key, name in [('td063Before', 'before.json'), ('td063Browser', 'browser/browser-report.json'),
                      ('td063Accounting', 'browser/accounting-report.json'), ('td063After', 'after.json')]:
        if evidence[key] != previous[name].upper():
            raise RuntimeError('TD-06.3 raw evidence drift: ' + key)
    if evidence['td063TerminalDiscovery'] != td063['terminalDiscoveryReadOnlyReportSha256'].upper():
        raise RuntimeError('TD-06.3 discovery evidence drift')
    if sha(BACKUP / 'manifest.json') != release['backupManifestSha256']:
        raise RuntimeError('Backup manifest changed')
    if load(BACKUP / 'COMPLETE.json')['manifestSha256'].upper() != evidence['td062BackupManifest']:
        raise RuntimeError('Backup seal mismatch')
    report = {
        'stage': 'TD-06.4', 'status': 'LOCAL_WINDOWS_MAIN443_DELIVERY_ARCHIVED',
        'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
        'mainOrigin': 'https://zj-market.test', 'candidateOrigin': 'https://zj-market.test:8445',
        'mainProject': 'zj-market-b06', 'source': {'a': head(A), 'b': head(B),
            'aFileCount': len(a_files), 'bFileCount': len(b_files),
            'sourceLockSha256': None, 'aSourceDigest': digest(a_files), 'bSourceDigest': digest(b_files)},
        'contract': {'coordinate': lock['coordinate'], 'jarSha256': lock['sha256'],
                     'apiJsonSha256': sha(B / 'docs/team-discovery-contract.json')},
        'build': {'aAppJarSha256': jar_a, 'bAppJarSha256': jar_b, 'mainWebBuild': web},
        'images': expected_images, 'allSevenServicesHealthy': len(running) == 7,
        'schema': {'aFingerprint': release['newSchema'], 'bFlywayHistorySha256': release['bMigrationHistory'],
                   'discoveryIndexColumns': deployment.index_state(), 'runtimeDdlGranted': False},
        'configTemplatesSha256': template_hashes, 'privateEvidenceSha256': evidence,
        'publicEvidenceSha256': paths(B, ['docs/tests/td04-acceptance.json',
            'docs/tests/td05-acceptance.json', 'docs/tests/td06-0-baseline-final.json',
            'docs/tests/td06-1-acceptance-verified.json', 'docs/tests/td06-2-acceptance.json',
            'docs/tests/td06-3-acceptance.json']),
        'backup': {'batch': release['backup'], 'consistentPointAtUtc': release['consistentPointAt'],
                   'preUpgradeOnly': True, 'doNotRestoreOverCurrentMainVolumes': True},
        'releaseState': {'gitCommitted': False, 'gitPushed': False, 'registryPublished': False,
                         'linuxValidated': False, 'externalClientsValidated': False},
        'publicFileAudit': {'a': public_file_audit(A), 'b': public_file_audit(B)},
        'limits': ['Local Windows Docker Desktop only', 'Simulated payment channel',
                   'Original pending obligations remain and must continue natural recovery',
                   'TD-06.3 did not force a live multi-page result'],
    }
    return sources, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['write', 'check'])
    mode = parser.parse_args().mode
    sources, report = collect()
    lock_bytes = (json.dumps(sources, ensure_ascii=False, indent=2) + '\n').encode()
    report['source']['sourceLockSha256'] = hashlib.sha256(lock_bytes).hexdigest().upper()
    if mode == 'write':
        if LOCK.exists() or OUT.exists():
            raise RuntimeError('Release files already exist; archive a new batch instead of overwriting')
        LOCK.write_bytes(lock_bytes)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    else:
        if LOCK.read_bytes() != lock_bytes:
            raise RuntimeError('TD-06 source lock drift')
        saved = load(OUT)
        report['generatedAtUtc'] = saved['generatedAtUtc']
        if report != saved:
            raise RuntimeError('TD-06 release manifest drift')
    print('PASS TD-06.4 local archive ' + mode)


if __name__ == '__main__':
    main()
