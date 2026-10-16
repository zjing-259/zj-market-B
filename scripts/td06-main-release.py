"""TD-06.2 guarded release of the existing 443 Compose project and volumes.

The sealed B-06.6 backup remains immutable. This tool never restores a volume.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

B = Path(__file__).resolve().parents[1]
A = Path('D:/Java/group-buy-market')
OLD = Path('D:/Java/zj-market-b-06')
BACKUP_NAME = 'b066-td062-20261015-03'
BACKUP = OLD / '.local/b06/backups' / BACKUP_NAME
WORK = B / 'target/team-discovery/td06_2_main_20261015_01'
PROJECT = 'zj-market-b06'
DOCKER = ['docker', '--context', 'desktop-linux']
SERVICES = ('mysql', 'redis', 'namesrv', 'broker', 'marketing-a', 'market-b', 'web')
INDEXES = {
    'idx_ab_team_discovery': ('ab_team', ('source', 'channel', 'goods_id', 'activity_id', 'team_status', 'valid_end_time', 'team_id')),
    'idx_ab_order_discovery_owner': ('ab_trade_order', ('team_id', 'user_id', 'order_status')),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run(args: list[str], *, sql: str | None = None, timeout: int = 300) -> str:
    result = subprocess.run([str(v) for v in args], input=sql, text=True,
                            capture_output=True, encoding='utf-8', errors='replace', timeout=timeout)
    if result.returncode:
        # Avoid logging secret-bearing command output or SQL.
        raise RuntimeError('Command failed: ' + ' '.join(str(v) for v in args[:5]))
    return result.stdout


def compose(mode: str, *args: str) -> str:
    return run(DOCKER + ['compose', '-p', PROJECT, '-f', str(WORK / ('compose-' + mode + '.json')), *args], timeout=360)


def sql(statement: str) -> str:
    return run(DOCKER + ['exec', '-i', PROJECT + '-mysql-1', 'sh', '-c',
               'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --skip-column-names'], sql=statement)


def release() -> dict:
    path = WORK / 'release.json'
    if not path.is_file():
        raise RuntimeError('Release must be prepared first')
    return load(path)


def backup_gate() -> dict:
    progress = load(BACKUP / 'progress.json')
    manifest = load(BACKUP / 'manifest.json')
    complete = load(BACKUP / 'COMPLETE.json')
    if (progress['status'] != 'BACKUP_COMPLETE' or not progress.get('originalRecovered')
            or manifest['project'] != PROJECT or manifest['runName'] != BACKUP_NAME
            or complete['manifestSha256'].upper() != sha(BACKUP / 'manifest.json')):
        raise RuntimeError('Latest backup is not sealed and original not recovered')
    if set(manifest['volumes']) != {'mysql-data', 'redis-data', 'broker-store', 'broker-logs', 'namesrv-logs'}:
        raise RuntimeError('Backup volume set changed')
    return manifest


def image_id(ref: str) -> str:
    image = json.loads(run(DOCKER + ['image', 'inspect', ref]))[0]
    if image['Architecture'] != 'amd64':
        raise RuntimeError('Wrong image architecture')
    return image['Id']


def verify_source() -> None:
    td05 = load(B / 'docs/team-discovery-td05-release.json')
    frozen = load(B / 'target/team-discovery/td05_20261015_01/a-source-hashes.json')
    if any(not (A / name).is_file() or sha(A / name) != digest for name, digest in frozen.items()):
        raise RuntimeError('A source differs from certified TD-05 image')
    if sha(B / 'zj-market-app/target/zj-market-app-exec.jar') != td05['buildContexts']['b']['app.jar']:
        raise RuntimeError('B jar differs from certified TD-05 image')
    if sha(B / 'frontend/src/services/team-discovery.ts') != load(B / 'docs/tests/td06-1-acceptance-verified.json')['sourceSha256']['frontend/src/services/team-discovery.ts']:
        raise RuntimeError('Frontend pagination source differs from TD-06.1')


def config_variant(base: dict, images: dict, mode: str, capability: Path) -> dict:
    cfg = json.loads(json.dumps(base))
    cfg['services']['marketing-a']['image'] = images['a']
    cfg['services']['marketing-a']['command'].append('--logging.config=file:/etc/b06/logback-td05.xml')
    cfg['services']['marketing-a']['volumes'].append({
        'type': 'bind', 'source': str(WORK / 'private/logback-a.xml'),
        'target': '/etc/b06/logback-td05.xml', 'read_only': True,
        'bind': {'create_host_path': False}})
    cfg['services']['market-b']['image'] = images['oldB'] if mode == 'rollback' else images['b']
    cfg['services']['web']['image'] = images['oldWeb'] if mode == 'rollback' else images['web']
    cfg['services']['market-b']['environment']['B_TEAM_DISCOVERY_ENABLED'] = 'true' if mode == 'on' else 'false'
    for mount in cfg['services']['market-b']['volumes']:
        if mount['target'] == '/etc/b06/capabilities.properties':
            mount['source'] = str(capability)
    for mount in cfg['services']['web']['volumes']:
        if mount['target'] == '/etc/b06/admission.conf':
            mount['source'] = str(BACKUP / 'bundle/config' / ('admission-maintenance.conf' if mode == 'maintenance' else 'admission-open.conf'))
    return cfg


def prepare() -> None:
    manifest = backup_gate()
    verify_source()
    old = load(B / 'docs/b06-final-release.json')['images']
    td05 = load(B / 'docs/team-discovery-td05-release.json')['images']
    images = {'a': td05['a']['id'], 'b': td05['b']['id'],
              'web': image_id('zj-market-td062/web:20261015-01'),
              'oldB': old['b'], 'oldWeb': old['web']}
    for key, ident in images.items():
        if image_id(ident) != ident:
            raise RuntimeError('Image ID unavailable: ' + key)
    base = load(BACKUP / 'compose-snapshot.json')
    if base['name'] != PROJECT or set(base['services']) != set(SERVICES) | {'mq-permissions'}:
        raise RuntimeError('Wrong source Compose project')
    if any(base['volumes'][n]['name'] != PROJECT + '_' + n for n in manifest['volumes']):
        raise RuntimeError('Source volume identity mismatch')
    capability = WORK / 'private/capabilities-open.properties'
    capability.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OLD / '.local/b06/control/capabilities.properties', capability)
    shutil.copyfile(B / 'target/team-discovery/td05_20261015_01/private/config/logback-td05.xml',
                    WORK / 'private/logback-a.xml')
    data = capability.read_text(encoding='utf-8')
    if not all(name + '=true' in data for name in ('b.payment.checkout-enabled', 'b.reconciliation.enabled', 'b.refund.enabled')):
        raise RuntimeError('Open business capabilities missing')
    for mode in ('maintenance', 'off', 'on', 'rollback'):
        cfg = config_variant(base, images, mode, capability)
        save(WORK / ('compose-' + mode + '.json'), cfg)
        run(DOCKER + ['compose', '-p', PROJECT, '-f', str(WORK / ('compose-' + mode + '.json')), 'config', '-q'])
    record = {'stage': 'TD-06.2', 'status': 'PREPARED', 'project': PROJECT,
              'backup': BACKUP_NAME, 'backupManifestSha256': sha(BACKUP / 'manifest.json'),
              'consistentPointAt': manifest['consistentPointAt'], 'images': images,
              'capabilitySha256': sha(capability), 'oldSchema': manifest['schemaFingerprint'],
              'bMigrationHistory': manifest['migrationHistoryHash'],
              'newSchema': load(B / 'docs/team-discovery-td05-release.json')['aSchemaFingerprint'],
              'events': []}
    save(WORK / 'release.json', record)
    print('PREPARED TD-06.2 with sealed current backup and exact original volumes')


def event(label: str, **facts: object) -> None:
    record = release()
    record['events'].append({'atUtc': datetime.now(timezone.utc).isoformat(), 'event': label, **facts})
    record['status'] = label
    save(WORK / 'release.json', record)
    print('PASS ' + label, flush=True)


def ddl_state() -> tuple[str, str]:
    import importlib.util
    spec = importlib.util.spec_from_file_location('b06_deploy', B / 'scripts/b06-deployment.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    obj = object.__new__(module.Deployment)
    obj.admin = lambda _label, statement: sql(statement)
    return obj.fingerprint(), obj.history()


def index_state() -> dict[str, list[str]]:
    raw = sql("SELECT TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX,COLUMN_NAME,NON_UNIQUE,COALESCE(SUB_PART,0),INDEX_TYPE FROM information_schema.STATISTICS "
              "WHERE TABLE_SCHEMA='group_buy_market_b06' AND INDEX_NAME IN "
              "('idx_ab_team_discovery','idx_ab_order_discovery_owner') ORDER BY TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX;")
    result = {name: [] for name in INDEXES}
    for row in raw.splitlines():
        table, name, seq, column, non_unique, prefix_length, index_type = row.split('\t')
        expected_table, _ = INDEXES[name]
        if (table != expected_table or int(seq) != len(result[name]) + 1
                or non_unique != '1' or prefix_length != '0' or index_type != 'BTREE'):
            raise RuntimeError('Discovery index name conflict: ' + name)
        result[name].append(column)
    for name, (_, columns) in INDEXES.items():
        if result[name] and tuple(result[name]) != columns:
            raise RuntimeError('Discovery index definition conflict: ' + name)
    return result


def containers(expected: dict[str, str] | None = None, *, healthy: bool = True) -> dict:
    rows = json.loads(run(DOCKER + ['inspect'] + [PROJECT + '-' + n + '-1' for n in SERVICES]))
    result = {}
    for name, row in zip(SERVICES, rows):
        labels = row['Config']['Labels']
        if labels.get('com.docker.compose.project') != PROJECT or labels.get('com.docker.compose.service') != name:
            raise RuntimeError('Container ownership mismatch: ' + name)
        if expected and name in expected and row['Image'] != expected[name]:
            raise RuntimeError('Image mismatch: ' + name)
        if healthy and (not row['State']['Running'] or row['State'].get('Health', {}).get('Status') != 'healthy'):
            raise RuntimeError('Service not healthy: ' + name)
        result[name] = row['Image']
    return result


def verify_schema(new: bool) -> None:
    record = release()
    schema, history = ddl_state()
    if schema != record['newSchema' if new else 'oldSchema'] or history != record['bMigrationHistory']:
        raise RuntimeError('Schema or Flyway gate failed')
    indexes = index_state()
    if new != all(indexes[name] for name in INDEXES):
        raise RuntimeError('Discovery index gate failed')
    grants = sql("SHOW GRANTS FOR 'a_runtime'@'%'; SHOW GRANTS FOR 'b_runtime'@'%';")
    if any(word in grants.upper() for word in ('ALTER', 'CREATE', 'DROP', 'INDEX', 'ALL PRIVILEGES')):
        raise RuntimeError('Runtime DDL grant detected')


def migrate() -> None:
    record = release()
    if record['status'] != 'PREPARED':
        raise RuntimeError('Wrong release phase for migration')
    backup_gate()
    # The old controller closes the gateway and stops every old writer before DDL.
    run(['python', '-B', OLD / 'scripts/b06-deployment.py', 'stop', '--context', 'desktop-linux'], timeout=300)
    event('OLD_STACK_STOPPED')
    compose('maintenance', 'up', '-d', '--wait', '--wait-timeout', '180', 'mysql', 'redis', 'namesrv', 'broker')
    verify_schema(False)
    for name, (table, columns) in INDEXES.items():
        existing = index_state()[name]
        if not existing:
            statement = 'CREATE INDEX ' + name + ' ON group_buy_market_b06.' + table + ' (' + ','.join(columns) + ');'
            sql(statement)
    verify_schema(True)
    event('INDEXES_APPLIED', indexColumns=index_state(), schemaFingerprint=record['newSchema'])


def rollout() -> None:
    record = release()
    if record['status'] not in ('INDEXES_APPLIED', 'A_LOGGING_REPAIRED'):
        raise RuntimeError('Migration gate required')
    verify_schema(True)
    compose('maintenance', 'up', '-d', '--wait', '--wait-timeout', '180', 'marketing-a')
    event('NEW_A_HEALTHY')
    compose('maintenance', 'up', '-d', '--wait', '--wait-timeout', '180', 'market-b', 'web')
    expected = {'marketing-a': record['images']['a'], 'market-b': record['images']['b'], 'web': record['images']['web']}
    containers(expected)
    verify_schema(True)
    event('NEW_STACK_MAINTENANCE_DISCOVERY_OFF', images=expected)


def repair_logging() -> None:
    record = release()
    if record['status'] != 'INDEXES_APPLIED':
        raise RuntimeError('Repair is only valid after the initial A logging failure')
    source = B / 'target/team-discovery/td05_20261015_01/private/config/logback-td05.xml'
    target = WORK / 'private/logback-a.xml'
    shutil.copyfile(source, target)
    for mode in ('maintenance', 'off', 'on', 'rollback'):
        path = WORK / ('compose-' + mode + '.json')
        cfg = load(path)
        a = cfg['services']['marketing-a']
        if '--logging.config=file:/etc/b06/logback-td05.xml' not in a['command']:
            a['command'].append('--logging.config=file:/etc/b06/logback-td05.xml')
            a['volumes'].append({'type': 'bind', 'source': str(target),
                                 'target': '/etc/b06/logback-td05.xml',
                                 'read_only': True, 'bind': {'create_host_path': False}})
        save(path, cfg)
        run(DOCKER + ['compose', '-p', PROJECT, '-f', str(path), 'config', '-q'])
    event('A_LOGGING_REPAIRED', logbackSha256=sha(target))


def signed_rpc_probe() -> str:
    import zipfile
    jar = B / 'target/team-discovery/td05_20261015_01/build/b/app.jar'
    probe = WORK / 'rpc-probe'
    classes, libs = probe / 'classes', probe / 'lib'
    classes.mkdir(parents=True, exist_ok=True)
    libs.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(jar) as archive:
        for name in archive.namelist():
            if name.startswith('BOOT-INF/classes/') and not name.endswith('/'):
                target = classes / Path(name).relative_to('BOOT-INF/classes')
            elif name.startswith('BOOT-INF/lib/') and name.endswith('.jar'):
                target = libs / Path(name).name
            else:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    run(['C:/Program Files/Java/jdk-21/bin/javac.exe', '-cp', str(classes) + ';' + str(libs / '*'),
         '-d', classes, B / 'docs/tests/td05/Td05RpcProbe.java'])
    row = sql("SELECT s.goods_id,s.activity_id,p.product_version,o.user_id FROM group_buy_market_b06.sc_sku_activity s "
              "JOIN zj_market_b06.b_product p ON p.goods_id=s.goods_id "
              "JOIN zj_market_b06.b_market_order o ON o.goods_id=s.goods_id "
              "WHERE o.business_status='GROUP_COMPLETED' ORDER BY o.order_id LIMIT 1;").strip().split('\t')
    if len(row) != 4 or not re.fullmatch(r'[0-9a-f-]{36}', row[0]):
        raise RuntimeError('No valid pre-existing main buyer for signed RPC')
    base = load(B / 'deploy/b06/images.lock.json')['java21']
    private = OLD / '.local/b06/runtime'
    cfg = OLD / 'deploy/b06/config'
    mounts = ['--mount', 'type=bind,src=' + str(probe) + ',dst=/probe,readonly',
              '--mount', 'type=bind,src=' + str(private) + ',dst=/private/runtime,readonly',
              '--mount', 'type=bind,src=' + str(cfg) + ',dst=/private/config,readonly']
    output = run(DOCKER + ['run', '--rm', '--network', PROJECT + '_rpc', '--memory', '384m',
                          '--read-only', '--tmpfs', '/tmp:rw,nosuid,size=64m', *mounts,
                          '--entrypoint', 'java', base, '-Duser.home=/tmp', '-cp',
                          '/probe/classes:/probe/lib/*', 'cn.zj.zjmarket.td05.Td05RpcProbe',
                          row[0], row[1], row[2], row[3]], timeout=180)
    if 'TD05_A_RPC_READY' not in output:
        raise RuntimeError('Signed TLS RPC marker missing')
    return next(line.strip() for line in output.splitlines() if 'TD05_A_RPC_READY' in line)


def rpc() -> None:
    record = release()
    if record['status'] != 'NEW_STACK_MAINTENANCE_DISCOVERY_OFF':
        raise RuntimeError('New off stack required before RPC probe')
    result = signed_rpc_probe()
    event('REAL_SIGNED_TLS_RPC_READY', result=result)


def public_gate(mode: str) -> None:
    output = run(['node', B / 'docs/tests/td06-main-gate.mjs', mode], timeout=90)
    if 'TD062_443_GATE_PASS ' + mode not in output:
        raise RuntimeError('443 public gate marker missing')


def old_ready(mode: str) -> None:
    output = run(['node', OLD / 'docs/tests/b06-startup-client.mjs', mode,
                  OLD / '.local/b06/control', OLD / '.local/b06/runtime'], timeout=150)
    if 'CLIENT_PASS' not in output:
        raise RuntimeError('Original flow readiness marker missing')


def off_gate() -> None:
    record = release()
    if record['status'] != 'REAL_SIGNED_TLS_RPC_READY':
        raise RuntimeError('Direct RPC gate required before off-mode public check')
    compose('off', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
    try:
        public_gate('off')
        old_ready('ready')
    finally:
        compose('maintenance', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
    event('OFF_443_AND_OLD_FLOW_READY')


def enable() -> None:
    record = release()
    if record['status'] != 'OFF_443_AND_OLD_FLOW_READY':
        raise RuntimeError('Signed RPC and off-mode public gates required')
    verify_schema(True)
    compose('on', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '180', 'market-b')
    # The public gateway remains maintenance until the updated B is healthy.
    containers({'marketing-a': record['images']['a'], 'market-b': record['images']['b']}, healthy=False)
    compose('on', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
    containers({'marketing-a': record['images']['a'], 'market-b': record['images']['b'], 'web': record['images']['web']})
    verify_schema(True)
    public_gate('on')
    old_ready('ready')
    event('ENABLED_443')


def money_stock() -> list[str]:
    rows = sql("SELECT 'paid',COALESCE(SUM(amount),0) FROM zj_market_b06.b_sim_payment WHERE gate='PAID'; "
               "SELECT 'refunded',COALESCE(SUM(refunded_amount),0) FROM zj_market_b06.b_sim_refund; "
               "SELECT 'available',COALESCE(SUM(available),0) FROM zj_market_b06.b_inventory_account; "
               "SELECT 'reserved',COALESCE(SUM(reserved),0) FROM zj_market_b06.b_inventory_account; "
               "SELECT 'sold',COALESCE(SUM(sold),0) FROM zj_market_b06.b_inventory_account;")
    return rows.splitlines()


def fallback() -> None:
    record = release()
    if record['status'] != 'ENABLED_443':
        raise RuntimeError('Enabled release required before fallback validation')
    before = money_stock()
    verify_schema(True)
    # Stop new writes before changing packages. The original B and web images are
    # the sealed pre-release IDs; same database and five volumes stay in place.
    compose('maintenance', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
    compose('rollback', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '180', 'market-b')
    compose('rollback', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
    containers({'marketing-a': record['images']['a'], 'market-b': record['images']['oldB'], 'web': record['images']['oldWeb']})
    public_gate('off')
    old_ready('ready')
    old_ready('hold')
    old_ready('cancel')
    old_ready('closed')
    if money_stock() != before:
        raise RuntimeError('Fallback old-flow funds or inventory changed')
    event('OLD_PACKAGE_FALLBACK_VERIFIED', moneyStock=before)
    # Return to the enabled release, still retaining original transactions.
    compose('maintenance', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
    compose('on', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '180', 'market-b')
    compose('on', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
    containers({'marketing-a': record['images']['a'], 'market-b': record['images']['b'], 'web': record['images']['web']})
    verify_schema(True)
    public_gate('on')
    if money_stock() != before:
        raise RuntimeError('Re-enabled release funds or inventory changed')
    event('RE_ENABLED_443_AFTER_FALLBACK')


def status() -> None:
    record = release()
    if record['status'] != 'STOPPED':
        verify_schema(True)
        expected = {'marketing-a': record['images']['a'],
                    'market-b': record['images']['b'], 'web': record['images']['web']}
        containers(expected)
        if record['status'] in ('RE_ENABLED_443_AFTER_FALLBACK', 'RESTARTED_443'):
            public_gate('on')
    print(json.dumps({'status': record['status'], 'project': PROJECT,
                      'images': containers(healthy=record['status'] != 'STOPPED')}, ensure_ascii=False))


def stop() -> None:
    record = release()
    if record['status'] not in ('RE_ENABLED_443_AFTER_FALLBACK', 'RESTARTED_443'):
        raise RuntimeError('Only a verified main release can be stopped')
    containers({'marketing-a': record['images']['a'], 'market-b': record['images']['b'],
                'web': record['images']['web']})
    compose('maintenance', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
    compose('maintenance', 'stop', 'web', 'market-b', 'marketing-a', 'broker', 'namesrv', 'redis', 'mysql')
    event('STOPPED')


def start() -> None:
    record = release()
    if record['status'] != 'STOPPED':
        raise RuntimeError('Main release must be stopped before controlled start')
    backup_gate()
    compose('maintenance', 'up', '-d', '--wait', '--wait-timeout', '180', 'mysql', 'redis', 'namesrv', 'broker')
    verify_schema(True)
    compose('maintenance', 'up', '-d', '--wait', '--wait-timeout', '180', 'marketing-a')
    compose('maintenance', 'up', '-d', '--wait', '--wait-timeout', '180', 'market-b', 'web')
    containers({'marketing-a': record['images']['a'], 'market-b': record['images']['b'],
                'web': record['images']['web']})
    signed_rpc_probe()
    compose('on', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '180', 'market-b')
    compose('on', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
    containers({'marketing-a': record['images']['a'], 'market-b': record['images']['b'],
                'web': record['images']['web']})
    public_gate('on')
    old_ready('ready')
    event('RESTARTED_443')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'migrate', 'repair_logging', 'rollout', 'rpc', 'off_gate', 'enable', 'fallback', 'status', 'stop', 'start'])
    action = parser.parse_args().action
    try:
        globals()[action]()
    except Exception:
        if action in ('rollout', 'off_gate', 'enable', 'fallback', 'start') and (WORK / 'compose-maintenance.json').is_file():
            try:
                compose('maintenance', 'up', '-d', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
            except Exception:
                # A failed maintenance recreate must not leave an open gateway.
                subprocess.run(DOCKER + ['stop', PROJECT + '-web-1'], capture_output=True, timeout=120)
            if (WORK / 'release.json').is_file():
                event('FAILED_GATE_CLOSED', action=action)
        raise


if __name__ == '__main__':
    main()
