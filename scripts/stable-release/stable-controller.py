"""Fixed-image TD-06 lifecycle controller. ST-03 must arm adoption before mutations."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

RELEASE = 'td06-stable-20261016-01'
PROJECT = 'zj-market-b06'
SERVICES = ('mysql', 'redis', 'namesrv', 'broker', 'marketing-a', 'market-b', 'web')
MIDDLEWARE = ('mysql', 'redis', 'namesrv', 'broker')
SCHEMA_SQL = (
    "SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,ORDINAL_POSITION,COLUMN_TYPE,IS_NULLABLE,COALESCE(COLUMN_DEFAULT,'<NULL>'),EXTRA,COALESCE(COLLATION_NAME,'') FROM information_schema.COLUMNS WHERE TABLE_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION; "
    "SELECT TABLE_SCHEMA,TABLE_NAME,INDEX_NAME,NON_UNIQUE,SEQ_IN_INDEX,COLUMN_NAME,COALESCE(SUB_PART,0) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY TABLE_SCHEMA,TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX; "
    "SELECT TABLE_SCHEMA,TABLE_NAME,ENGINE,TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY TABLE_SCHEMA,TABLE_NAME; "
    "SELECT CONSTRAINT_SCHEMA,TABLE_NAME,CONSTRAINT_NAME,CONSTRAINT_TYPE,ENFORCED FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY CONSTRAINT_SCHEMA,TABLE_NAME,CONSTRAINT_NAME; "
    "SELECT CONSTRAINT_SCHEMA,TABLE_NAME,CONSTRAINT_NAME,COLUMN_NAME,ORDINAL_POSITION,COALESCE(REFERENCED_TABLE_SCHEMA,''),COALESCE(REFERENCED_TABLE_NAME,''),COALESCE(REFERENCED_COLUMN_NAME,'') FROM information_schema.KEY_COLUMN_USAGE WHERE CONSTRAINT_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY CONSTRAINT_SCHEMA,TABLE_NAME,CONSTRAINT_NAME,ORDINAL_POSITION; "
    "SELECT CONSTRAINT_SCHEMA,CONSTRAINT_NAME,CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY CONSTRAINT_SCHEMA,CONSTRAINT_NAME; "
    "SELECT CONSTRAINT_SCHEMA,TABLE_NAME,CONSTRAINT_NAME,UPDATE_RULE,DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY CONSTRAINT_SCHEMA,TABLE_NAME,CONSTRAINT_NAME;"
)
INDEX_SQL = ("SELECT TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX,COLUMN_NAME,NON_UNIQUE,COALESCE(SUB_PART,0),INDEX_TYPE "
             "FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='group_buy_market_b06' AND INDEX_NAME IN "
             "('idx_ab_team_discovery','idx_ab_order_discovery_owner') ORDER BY TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX;")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest().upper()


def normalized_host(path: str) -> Path:
    match = re.match(r'^/run/desktop/mnt/host/([a-z])/(.*)$', path, re.I)
    if match:
        path = match.group(1).upper() + ':/' + match.group(2)
    return Path(path).resolve()


class Controller:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.release_dir = self.root / 'releases' / RELEASE
        self.private_dir = self.root / 'private'
        self.state_dir = self.root / 'state'
        self.release_path = self.release_dir / 'release.json'
        self.release = load(self.release_path)
        self.private_manifest = load(self.private_dir / 'files-manifest.json')
        if self.release['release'] != RELEASE or self.release['project'] != PROJECT:
            raise RuntimeError('Wrong stable release identity')
        self.docker = [self.release['dockerExecutable'], '--context', 'desktop-linux']

    def run(self, label: str, args: list[str], *, input_text: str | None = None, timeout: int = 300) -> str:
        result = subprocess.run([str(v) for v in args], input=input_text, text=True,
                                capture_output=True, encoding='utf-8', errors='replace', timeout=timeout)
        if result.returncode:
            raise RuntimeError(label + ' failed; details kept out of public output')
        return result.stdout

    def check_bundle(self) -> None:
        if sha(self.private_dir / 'files-manifest.json') != self.release['privateManifestSha256']:
            raise RuntimeError('Private manifest drift')
        for item in self.private_manifest['files']:
            path = (self.private_dir / item['relativePath']).resolve()
            if not path.is_relative_to(self.private_dir) or not path.is_file() or sha(path) != item['sha256']:
                raise RuntimeError('Private file drift: ' + Path(item['relativePath']).name)
        for item in self.release['templates'].values():
            path = (self.root / item['file']).resolve()
            if not path.is_relative_to(self.release_dir) or sha(path) != item['sha256']:
                raise RuntimeError('Compose template drift')
        for name, expected in self.release['tools'].items():
            if sha(self.release_dir / name) != expected:
                raise RuntimeError('Release tool drift: ' + name)

    def docker_inventory(self) -> None:
        for role, expected in self.release['images'].items():
            actual = load_text_json(self.run('image inspect ' + role,
                self.docker + ['image', 'inspect', expected]))[0]['Id']
            if actual != expected:
                raise RuntimeError('Image ID changed: ' + role)
        volumes = load_text_json(self.run('volume inspect', self.docker + ['volume', 'inspect', *self.release['volumes']]))
        if {value['Name'] for value in volumes} != set(self.release['volumes']):
            raise RuntimeError('Existing five volumes missing')
        if any(value['CreatedAt'] != self.release['volumeIdentity'][value['Name']] or
               (value.get('Labels') or {}).get('com.docker.compose.project') != PROJECT for value in volumes):
            raise RuntimeError('Original volume identity changed')
        networks = load_text_json(self.run('network inspect', self.docker + ['network', 'inspect', *self.release['networks']]))
        if {value['Name'] for value in networks} != set(self.release['networks']):
            raise RuntimeError('Existing networks missing')
        if any(value['Id'] != self.release['networkIdentity'][value['Name']] for value in networks):
            raise RuntimeError('Original network identity changed')

    def rendered(self, mode: str) -> dict:
        if mode not in ('on', 'maintenance'):
            raise RuntimeError('Unsupported gateway mode')
        template = load(self.root / self.release['templates'][mode]['file'])
        def resolve(value):
            if isinstance(value, str) and value.startswith('@private/'):
                path = (self.private_dir / value.removeprefix('@private/')).resolve()
                if not path.is_relative_to(self.private_dir):
                    raise RuntimeError('Private path escapes bundle')
                return str(path)
            if isinstance(value, list):
                return [resolve(item) for item in value]
            if isinstance(value, dict):
                return {key: resolve(item) for key, item in value.items()}
            return value
        return resolve(template)

    def compose_path(self, mode: str) -> Path:
        path = self.state_dir / ('compose-' + mode + '.json')
        self.atomic(path, self.rendered(mode))
        self.run('Compose validation', self.docker + ['compose', '-p', PROJECT, '-f', str(path), 'config', '-q'])
        return path

    def compose(self, mode: str, *args: str) -> str:
        path = self.state_dir / ('compose-' + mode + '.json')
        if not path.is_file():
            raise RuntimeError('Compose was not prepared')
        return self.run('Compose ' + ' '.join(args[:2]),
                        self.docker + ['compose', '-p', PROJECT, '-f', str(path), *args], timeout=420)

    def inspect(self) -> dict[str, dict]:
        names = [PROJECT + '-' + name + '-1' for name in SERVICES]
        existing = self.run('container listing', self.docker + ['ps', '-a', '--filter',
            'label=com.docker.compose.project=' + PROJECT, '--format', '{{.Names}}']).splitlines()
        present = set(names) & set(existing)
        if not present:
            return {}
        if present != set(names):
            raise RuntimeError('Partial main project container set')
        rows = load_text_json(self.run('container inspect', self.docker + ['inspect', *names]))
        result = {}
        for name, row in zip(SERVICES, rows):
            labels = row['Config']['Labels'] or {}
            if labels.get('com.docker.compose.project') != PROJECT or labels.get('com.docker.compose.service') != name:
                raise RuntimeError('Container ownership mismatch: ' + name)
            expected = self.release['images'][self.release['serviceImageRoles'][name]]
            if row['Image'] != expected:
                raise RuntimeError('Running image mismatch: ' + name)
            result[name] = row
        return result

    def adopted(self, rows: dict[str, dict]) -> bool:
        if not rows:
            return False
        compose = self.rendered('on')
        for name in SERVICES:
            service = compose['services'][name]
            expected = {item['target']: item['source'] for item in service.get('volumes', [])
                        if item.get('type') == 'bind'}
            for secret in service.get('secrets', []):
                expected['/run/secrets/' + secret['target']] = compose['secrets'][secret['source']]['file']
            actual = {item['Destination']: item['Source'] for item in rows[name]['Mounts'] if item['Type'] == 'bind'}
            if set(actual) != set(expected):
                return False
            if any(normalized_host(actual[target]) != Path(source).resolve() for target, source in expected.items()):
                return False
        return True

    def running_healthy(self, rows: dict[str, dict]) -> bool:
        return bool(rows) and all(row['State']['Running'] and
            row['State'].get('Health', {}).get('Status') == 'healthy' for row in rows.values())

    def gateway_mode(self) -> str:
        config = self.run('gateway config', self.docker + ['exec', PROJECT + '-web-1', 'nginx', '-T'])
        marker = '# configuration file /etc/b06/admission.conf:'
        if marker not in config:
            raise RuntimeError('Gateway admission include missing')
        excerpt = config.split(marker, 1)[1].split('# configuration file ', 1)[0]
        match = re.search(r'map\s+"\$request_method:\$uri"\s+\$b06_block_new\s*\{(.*?)\}', excerpt, re.S)
        if not match or not re.search(r'\bdefault\s+0\s*;', match.group(1)):
            raise RuntimeError('Gateway admission mode unknown')
        block = bool(re.search(r'~\^\(POST\|PUT\|PATCH\|DELETE\):/api/\s+1\s*;', match.group(1)))
        return 'MAINTENANCE' if block else 'OPEN'

    def sql(self, statement: str) -> str:
        return self.run('read-only schema query', self.docker + ['exec', '-i', PROJECT + '-mysql-1',
            'sh', '-c', 'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --skip-column-names'],
            input_text=statement, timeout=90)

    def schema(self) -> None:
        if hashlib.sha256(self.sql(SCHEMA_SQL).encode()).hexdigest() != self.release['schemaFingerprint']:
            raise RuntimeError('Schema fingerprint drift')
        history = self.sql('SELECT version,script,checksum,success FROM zj_market_b06.flyway_schema_history ORDER BY installed_rank;')
        if hashlib.sha256(history.encode()).hexdigest() != self.release['flywayHistorySha256']:
            raise RuntimeError('Flyway history drift')
        indexes = {name: [] for name in self.release['discoveryIndexColumns']}
        for line in self.sql(INDEX_SQL).splitlines():
            table, name, seq, column, non_unique, sub_part, index_type = line.split('\t')
            if name not in indexes or table != ('ab_team' if name == 'idx_ab_team_discovery' else 'ab_trade_order') or \
                    int(seq) != len(indexes[name]) + 1 or non_unique != '1' or sub_part != '0' or index_type != 'BTREE':
                raise RuntimeError('Discovery index definition changed')
            indexes[name].append(column)
        if indexes != self.release['discoveryIndexColumns']:
            raise RuntimeError('Discovery indexes changed')

    def probe(self) -> None:
        items = self.private_manifest['probe']
        arguments = [str(self.private_dir / items[name]['relativePath'])
                     for name in ('web-ca.pem', 'demo-accounts.json', 'seed-goods-id.txt')]
        response = load_text_json(self.run('strict TLS business probe',
            [self.release['nodeExecutable'], str(self.release_dir / 'stable-probe.mjs'), *arguments], timeout=100))
        if response.get('status') != 'STABLE_PROBE_PASS' or response.get('invalidWrite') != 401:
            raise RuntimeError('Business probe marker missing')

    def read_status(self) -> dict:
        self.check_bundle()
        rows = self.inspect()
        if not rows:
            status = 'ABSENT'
        elif not any(row['State']['Running'] for row in rows.values()):
            status = 'STOPPED_ADOPTED' if self.adopted(rows) else 'STOPPED_LEGACY'
        elif not self.running_healthy(rows):
            status = 'PARTIAL_OR_UNHEALTHY'
        else:
            status = 'READY' if self.adopted(rows) and self.gateway_mode() == 'OPEN' else 'LEGACY_OR_MAINTENANCE'
        return {'status': status, 'project': PROJECT, 'adopted': bool(rows) and self.adopted(rows),
                'running': sum(row['State']['Running'] for row in rows.values())}

    def ready(self) -> dict:
        self.check_bundle()
        self.docker_inventory()
        rows = self.inspect()
        if not self.running_healthy(rows) or not self.adopted(rows):
            raise RuntimeError('Stable bundle has not adopted a healthy main stack')
        if self.gateway_mode() != 'OPEN':
            raise RuntimeError('Main gateway is not open')
        self.schema()
        self.probe()
        return {'status': 'READY', 'project': PROJECT, 'release': RELEASE}

    def armed(self) -> None:
        receipt = self.state_dir / 'adoption.json'
        if not receipt.is_file():
            raise RuntimeError('ST-03 adoption receipt required before lifecycle mutation')
        data = load(receipt)
        if (data.get('release') != RELEASE or data.get('project') != PROJECT or
                data.get('releaseSha256') != sha(self.release_path) or
                data.get('backupBatch') is None or data.get('backupManifestSha256') is None):
            raise RuntimeError('ST-03 adoption receipt invalid')

    def preflight(self) -> None:
        self.check_bundle()
        self.docker_inventory()
        self.compose_path('on')
        self.compose_path('maintenance')

    def start(self) -> dict:
        with self.lock():
            self.armed()
            self.preflight()
            rows = self.inspect()
            if self.running_healthy(rows):
                if not self.adopted(rows) or self.gateway_mode() != 'OPEN':
                    raise RuntimeError('Running stack is not an adopted open release')
                return self.ready()
            if rows and any(row['State']['Running'] for row in rows.values()):
                raise RuntimeError('Partial running state; diagnose before start')
            # Compose does not include top-level secret file paths in every service
            # hash (Redis is unchanged); force recreation only during legacy adoption.
            recreate = ('--force-recreate',) if rows and not self.adopted(rows) else ()
            changed = False
            try:
                changed = True
                self.compose('maintenance', 'up', '-d', '--pull', 'never', '--no-build', *recreate, '--wait',
                             '--wait-timeout', '180', *MIDDLEWARE)
                self.schema()
                self.compose('maintenance', 'up', '-d', '--pull', 'never', '--no-build', *recreate, '--wait',
                             '--wait-timeout', '180', 'marketing-a', 'market-b', 'web')
                if self.gateway_mode() != 'MAINTENANCE':
                    raise RuntimeError('Gateway did not enter maintenance before opening')
                # B's maintenance capabilities disable discovery; restore its open
                # configuration while the public gateway is still closed.
                self.compose('on', 'up', '-d', '--pull', 'never', '--no-build', '--no-deps',
                             '--force-recreate', '--wait', '--wait-timeout', '180', 'market-b')
                self.compose('on', 'up', '-d', '--pull', 'never', '--no-build', '--no-deps',
                             '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
                result = self.ready()
                self.record('READY')
                return result
            except Exception:
                if changed:
                    self.close_after_failure()
                    self.record('FAILED_GATE_CLOSED')
                raise

    def stop(self) -> dict:
        with self.lock():
            self.armed()
            self.preflight()
            rows = self.inspect()
            if not self.running_healthy(rows) or not self.adopted(rows) or self.gateway_mode() != 'OPEN':
                raise RuntimeError('Only an adopted open and healthy release can be stopped')
            try:
                self.compose('maintenance', 'up', '-d', '--pull', 'never', '--no-build', '--no-deps',
                             '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
                if self.gateway_mode() != 'MAINTENANCE':
                    raise RuntimeError('Gateway maintenance could not be verified')
                self.record('STOPPING')
                self.compose('maintenance', 'stop', 'web', 'market-b', 'marketing-a', 'broker', 'namesrv', 'redis', 'mysql')
                self.record('STOPPED')
                return {'status': 'STOPPED', 'project': PROJECT}
            except Exception:
                self.close_after_failure()
                self.record('FAILED_GATE_CLOSED')
                raise

    def close_after_failure(self) -> None:
        try:
            self.compose('maintenance', 'up', '-d', '--pull', 'never', '--no-build', '--no-deps',
                         '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
            if self.gateway_mode() == 'MAINTENANCE':
                return
        except Exception:
            pass
        try:
            self.run('stop unsafe web', self.docker + ['stop', PROJECT + '-web-1'], timeout=120)
        except Exception:
            pass

    def open(self) -> dict:
        self.ready()
        script = self.release_dir / 'open-stable.ps1'
        self.run('open stable browser', ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                                        '-File', str(script), '-Root', str(self.root)], timeout=60)
        return {'status': 'BROWSER_OPENED', 'release': RELEASE}

    def atomic(self, path: Path, value: dict) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=self.state_dir, delete=False) as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            temporary = Path(stream.name)
        os.replace(temporary, path)

    def record(self, status: str) -> None:
        value = {'status': status, 'release': RELEASE, 'atUtc': datetime.now(timezone.utc).isoformat()}
        self.atomic(self.state_dir / 'state.json', value)
        with (self.state_dir / 'lifecycle.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(value) + '\n')

    @contextlib.contextmanager
    def lock(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with (self.state_dir / 'command.lock').open('a+b') as stream:
            stream.seek(0)
            stream.write(b'0')
            stream.flush()
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                try:
                    yield
                finally:
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    yield
                finally:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def load_text_json(value: str):
    return json.loads(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('status', 'ready', 'start', 'stop', 'open'))
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    controller = Controller(args.root)
    result = controller.read_status() if args.action == 'status' else getattr(controller, args.action)()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('STABLE_ERROR ' + str(error))
        raise SystemExit(1)
