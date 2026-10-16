"""Explicit TD-06.1 environment entry. Never substitutes the TD-05 clone for 443.

Candidate start/stop operates only on its sealed TD-05 Compose project and volumes.
After TD-06.2 the main 443 lifecycle delegates to the guarded TD-06 release
controller; historical pre-upgrade checks use the B-06 controller only before
the TD-06.2 private release record exists.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = Path('D:/Java/zj-market-b-06')
WORK = ROOT / 'target/team-discovery/td05_20261015_01'
PROJECT = 'zj-market-td05-20261015-01'
SERVICES = ('mysql', 'redis', 'namesrv', 'broker', 'marketing-a', 'market-b', 'web')
DOCKER = ['docker', '--context', 'desktop-linux']


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run(args: list[str], *, sql: str | None = None) -> str:
    result = subprocess.run([str(x) for x in args], input=sql, capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=300)
    if result.returncode:
        raise RuntimeError('Environment check failed: ' + ' '.join(str(x) for x in args[:5]))
    return result.stdout


def mysql(project: str, sql: str) -> str:
    return run(DOCKER + ['exec', '-i', project + '-mysql-1', 'sh', '-c',
               'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --skip-column-names'], sql=sql)


def ddl_state(project: str) -> tuple[str, str]:
    spec = importlib.util.spec_from_file_location('b06_ddl', ROOT / 'scripts/b06-deployment.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    deployment = object.__new__(module.Deployment)
    deployment.admin = lambda _label, sql: mysql(project, sql)
    return deployment.fingerprint(), deployment.history()


def validate_candidate_config(config: dict, release: dict) -> None:
    if config.get('name') != PROJECT or set(config.get('services', {})) != set(SERVICES) | {'mq-permissions'}:
        raise RuntimeError('Wrong candidate project or service set')
    expected = {'marketing-a': release['images']['a']['id'],
                'market-b': release['images']['b']['id'], 'web': release['images']['web']['id']}
    if any(config['services'][name].get('image') != image for name, image in expected.items()):
        raise RuntimeError('Candidate image differs from TD-05 release')
    ports = config['services']['web'].get('ports', [])
    if len(ports) != 1 or str(ports[0].get('published')) != '8445' or ports[0].get('host_ip') != '127.0.0.1':
        raise RuntimeError('Candidate must bind only loopback 8445')
    if set(config['volumes']) != {'mysql-data', 'redis-data', 'broker-store', 'broker-logs', 'namesrv-logs'}:
        raise RuntimeError('Unexpected candidate volumes')
    if any(value.get('name') != PROJECT + '_' + name or value.get('external') is not True
           for name, value in config['volumes'].items()):
        raise RuntimeError('Candidate volume ownership mismatch')
    if any(value.get('name') != PROJECT + '_' + name for name, value in config['networks'].items()):
        raise RuntimeError('Candidate network ownership mismatch')
    for value in config['secrets'].values():
        if not value.get('name', '').startswith(PROJECT + '_') or not Path(value['file']).resolve().is_relative_to(WORK.resolve()):
            raise RuntimeError('Candidate secret path or ownership mismatch')
    for value in config['services'].values():
        for mount in value.get('volumes', []):
            if mount.get('type') == 'bind' and (not mount.get('read_only') or
                    not Path(mount['source']).resolve().is_relative_to(WORK.resolve())):
                raise RuntimeError('Candidate bind mount escapes owned work or is writable')


def containers(project: str, expected: dict[str, str], *, require_healthy: bool) -> dict:
    rows = json.loads(run(DOCKER + ['inspect'] + [project + '-' + name + '-1' for name in SERVICES]))
    result = {}
    for name, row in zip(SERVICES, rows):
        labels = row['Config']['Labels']
        if labels.get('com.docker.compose.project') != project or labels.get('com.docker.compose.service') != name:
            raise RuntimeError('Container ownership mismatch: ' + name)
        if name in expected and row['Image'] != expected[name]:
            raise RuntimeError('Running image mismatch: ' + name)
        health = row['State'].get('Health', {}).get('Status', 'unknown')
        if require_healthy and (not row['State']['Running'] or health != 'healthy' or row['State']['OOMKilled']):
            raise RuntimeError('Service not healthy: ' + name)
        result[name] = {'image': row['Image'], 'running': row['State']['Running'], 'health': health}
    return result


def candidate_volumes() -> None:
    names = [PROJECT + '_' + name for name in ('mysql-data', 'redis-data', 'broker-store', 'broker-logs', 'namesrv-logs')]
    rows = json.loads(run(DOCKER + ['volume', 'inspect'] + names))
    for name, row in zip(names, rows):
        labels = row.get('Labels') or {}
        if row['Name'] != name or labels.get('com.docker.compose.project') != PROJECT or labels.get('td05.owner') != 'td05_20261015_01':
            raise RuntimeError('Candidate volume ownership mismatch: ' + name)


def candidate(action: str) -> None:
    release = load(ROOT / 'docs/team-discovery-td05-release.json')
    config = load(WORK / 'compose.json')
    validate_candidate_config(config, release)
    baseline = load(ROOT / 'docs/tests/td06-0-baseline-final.json')['candidate8445']
    for name, digest in baseline['configSha256'].items():
        if sha(WORK / name) != digest:
            raise RuntimeError('Candidate configuration drift: ' + name)
    candidate_volumes()
    expected = {'marketing-a': release['images']['a']['id'],
                'market-b': release['images']['b']['id'], 'web': release['images']['web']['id']}
    compose = DOCKER + ['compose', '-p', PROJECT, '-f', str(WORK / 'compose.json')]
    if action == 'stop':
        containers(PROJECT, expected, require_healthy=False)
        for service in ('web', 'market-b', 'marketing-a', 'broker', 'namesrv', 'redis', 'mysql'):
            run(compose + ['stop', service])
        print('STOPPED candidate8445; owned volumes retained')
        return
    if action == 'start':
        # Existing resource identities are checked before Compose may recreate a container.
        existing = run(DOCKER + ['ps', '-a', '--filter', 'label=com.docker.compose.project=' + PROJECT,
                                 '--format', '{{.Names}}']).splitlines()
        allowed = {PROJECT + '-' + x + '-1' for x in SERVICES} | {PROJECT + '-mq-permissions-1'}
        if existing and not set(existing).issubset(allowed):
            raise RuntimeError('Unexpected candidate container set')
        if existing:
            containers(PROJECT, expected, require_healthy=False)
        # An explicit start closes admission before any database or RPC gate.
        if existing:
            run(compose + ['stop', 'web'])
        run(compose + ['up', '-d', '--wait', '--wait-timeout', '180', 'mysql', 'redis', 'namesrv', 'broker'])
        schema, history = ddl_state(PROJECT)
        if schema != release['aSchemaFingerprint'] or history != release['bMigrationHistorySha256']:
            raise RuntimeError('Candidate schema/history gate failed; application was not started')
        try:
            run(compose + ['up', '-d', '--wait', '--wait-timeout', '180', 'marketing-a', 'market-b', 'web'])
        except Exception:
            run(compose + ['stop', 'web'])
            raise
    try:
        state = containers(PROJECT, expected, require_healthy=action in ('ready', 'start'))
        if action in ('ready', 'start'):
            schema, history = ddl_state(PROJECT)
            if schema != release['aSchemaFingerprint'] or history != release['bMigrationHistorySha256']:
                raise RuntimeError('Candidate schema/history drift')
            indexes = mysql(PROJECT, "SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='group_buy_market_b06' AND INDEX_NAME IN ('idx_ab_team_discovery','idx_ab_order_discovery_owner');").strip()
            if indexes != '10':
                raise RuntimeError('Candidate discovery indexes missing')
            run(['node', str(ROOT / 'docs/tests/td05-release-gate.mjs'), str(WORK), 'on'])
    except Exception:
        if action == 'start':
            run(compose + ['stop', 'web'])
        raise
    print(json.dumps({'target': 'candidate8445', 'project': PROJECT, 'action': action,
                      'services': {name: value['health'] for name, value in state.items()}}, ensure_ascii=False))


def main_environment(action: str) -> None:
    release = ROOT / 'target/team-discovery/td06_2_main_20261015_01/release.json'
    if release.is_file() and load(release).get('project') == 'zj-market-b06':
        if action == 'ready' and load(release).get('status') not in ('RE_ENABLED_443_AFTER_FALLBACK', 'RESTARTED_443'):
            raise RuntimeError('Main 443 release has not passed the enabled gate')
        release_action = {'ready': 'status', 'status': 'status', 'start': 'start', 'stop': 'stop'}[action]
        output = run(['python', '-B', str(ROOT / 'scripts/td06-main-release.py'), release_action])
        print(output.strip())
        return
    baseline = load(ROOT / 'docs/tests/td06-0-baseline-final.json')['main443']
    expected = {name: baseline['images'][name] for name in ('marketing-a', 'market-b', 'web')}
    project = 'zj-market-b06'
    if action in ('start', 'stop'):
        containers(project, expected, require_healthy=False)
        legacy_action = 'open' if action == 'start' else 'stop'
        run(['python', '-B', str(LEGACY / 'scripts/b06-deployment.py'), legacy_action, '--context', 'desktop-linux'])
    state = containers(project, expected, require_healthy=action in ('ready', 'start'))
    if action in ('ready', 'start'):
        schema, history = ddl_state(project)
        if schema != baseline['schemaFingerprint'] or history != baseline['migrationHistorySha256']:
            raise RuntimeError('Main 443 schema/history drift')
    print(json.dumps({'target': 'main443', 'project': project, 'action': action,
                      'services': {name: value['health'] for name, value in state.items()}}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('status', 'ready', 'start', 'stop'))
    parser.add_argument('--target', required=True, choices=('main443', 'candidate8445'))
    args = parser.parse_args()
    (candidate if args.target == 'candidate8445' else main_environment)(args.action)


if __name__ == '__main__':
    main()
