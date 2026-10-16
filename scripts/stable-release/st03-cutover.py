"""One-time TD-06 main-stack cold backup and adoption. Never restore over live volumes."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

B = Path(__file__).resolve().parents[2]
STABLE = Path('D:/Java/zj-market-stable')
SOURCE = B / 'target/stable-isolation/st03_20261016_04/bundle'
OLD = B / 'target/team-discovery/td06_2_main_20261015_01'
PROJECT = 'zj-market-b06'
RELEASE = 'td06-stable-20261016-01'
SERVICES = ('mysql', 'redis', 'namesrv', 'broker', 'marketing-a', 'market-b', 'web')
VOLUMES = ('mysql-data', 'redis-data', 'namesrv-logs', 'broker-logs', 'broker-store')

spec = importlib.util.spec_from_file_location('stable_control', B / 'scripts/stable-release/stable-controller.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return module.sha(path)


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def restrict_private(path: Path) -> None:
    if os.name != 'nt':
        path.chmod(0o700)
        return
    account = run('current account', ['whoami']).strip()
    run('restrict backup ACL', ['icacls', str(path), '/inheritance:r'])
    run('grant backup ACL', ['icacls', str(path), '/grant:r', account + ':F',
                             'SYSTEM:F', 'Administrators:F'])


def run(label: str, args: list[str], *, input_text: str | None = None, timeout: int = 600) -> str:
    result = subprocess.run([str(v) for v in args], input=input_text, text=True,
                            capture_output=True, encoding='utf-8', errors='replace', timeout=timeout)
    if result.returncode:
        raise RuntimeError(label + ' failed; process details withheld')
    return result.stdout


def raw_to_file(label: str, args: list[str], path: Path, timeout: int = 600) -> None:
    with path.open('wb') as output:
        result = subprocess.run([str(v) for v in args], stdout=output, stderr=subprocess.DEVNULL, timeout=timeout)
    if result.returncode or path.stat().st_size == 0:
        raise RuntimeError(label + ' failed')


def old_compose(mode: str, *args: str) -> str:
    return run('old Compose', ['docker', '--context', 'desktop-linux', 'compose', '-p', PROJECT,
                                '-f', str(OLD / ('compose-' + mode + '.json')), *args], timeout=450)


def record(basedir: Path, phase: str, **facts) -> None:
    write(basedir / 'journal.json', {'phase': phase, 'atUtc': stamp(), **facts})
    print('ST03_PHASE ' + phase, flush=True)


def data_snapshot(control: module.Controller) -> dict:
    statements = {
        'moneyStock': "SELECT 'paid',COALESCE(SUM(amount),0) FROM zj_market_b06.b_sim_payment WHERE gate='PAID'; "
                      "SELECT 'refunded',COALESCE(SUM(refunded_amount),0) FROM zj_market_b06.b_sim_refund; "
                      "SELECT 'available',COALESCE(SUM(available),0) FROM zj_market_b06.b_inventory_account; "
                      "SELECT 'reserved',COALESCE(SUM(reserved),0) FROM zj_market_b06.b_inventory_account; "
                      "SELECT 'sold',COALESCE(SUM(sold),0) FROM zj_market_b06.b_inventory_account;",
        'obligations': "SELECT 'aReconciling',COUNT(*) FROM group_buy_market_b06.ab_team WHERE team_status='RECONCILING'; "
                       "SELECT 'aPaid',COUNT(*) FROM group_buy_market_b06.ab_trade_order WHERE order_status='PAID'; "
                       "SELECT 'bTradeWork',COUNT(*) FROM zj_market_b06.b_trade_work WHERE state NOT IN ('DONE','DEAD'); "
                       "SELECT 'bTradeInbox',COUNT(*) FROM zj_market_b06.b_trade_inbox WHERE state NOT IN ('DONE','DEAD'); "
                       "SELECT 'bTradeOutbox',COUNT(*) FROM zj_market_b06.b_trade_outbox WHERE state NOT IN ('DONE','DEAD'); "
                       "SELECT 'bRefundTask',COUNT(*) FROM zj_market_b06.b_refund_task WHERE state NOT IN ('DONE','DEAD');",
    }
    return {name: control.sql(statement).splitlines() for name, statement in statements.items()}


def validate_source(control: module.Controller) -> None:
    control.check_bundle()
    control.docker_inventory()
    rows = control.inspect()
    if not control.running_healthy(rows) or control.adopted(rows) or control.gateway_mode() != 'OPEN':
        raise RuntimeError('Source must be healthy open legacy main stack')
    control.schema()
    control.probe()


def old_recover() -> None:
    old_compose('maintenance', 'up', '-d', '--pull', 'never', '--no-build', '--wait', '--wait-timeout', '180',
                'mysql', 'redis', 'namesrv', 'broker')
    old_compose('maintenance', 'up', '-d', '--pull', 'never', '--no-build', '--wait', '--wait-timeout', '180',
                'marketing-a', 'market-b', 'web')
    old_compose('on', 'up', '-d', '--pull', 'never', '--no-build', '--no-deps', '--force-recreate',
                '--wait', '--wait-timeout', '180', 'market-b')
    old_compose('on', 'up', '-d', '--pull', 'never', '--no-build', '--no-deps', '--force-recreate',
                '--wait', '--wait-timeout', '90', 'web')


def adoption_diagnostics(control: module.Controller) -> dict:
    rows = control.inspect()
    expected = control.rendered('on')
    details = {}
    for name in SERVICES:
        service = expected['services'][name]
        paths = {item['target']: item['source'] for item in service.get('volumes', [])
                 if item.get('type') == 'bind'}
        for secret in service.get('secrets', []):
            paths['/run/secrets/' + secret['target']] = expected['secrets'][secret['source']]['file']
        actual = {item['Destination']: item['Source'] for item in rows[name]['Mounts'] if item['Type'] == 'bind'}
        details[name] = {'healthy': rows[name]['State'].get('Health', {}).get('Status') == 'healthy',
                         'bindTargetsMatch': set(actual) == set(paths),
                         'bindSourcesMatch': set(actual) == set(paths) and all(
                             module.normalized_host(actual[target]) == Path(source).resolve()
                             for target, source in paths.items())}
    return {'runningHealthy': control.running_healthy(rows), 'adopted': control.adopted(rows),
            'gatewayMode': control.gateway_mode(), 'services': details}


def cutover(root: Path, batch: str) -> None:
    if root.resolve() != STABLE.resolve() or not root.is_dir():
        raise RuntimeError('Expected independent D:/Java/zj-market-stable directory')
    control = module.Controller(root)
    if sha(root / 'releases' / RELEASE / 'release.json') != sha(SOURCE / 'releases' / RELEASE / 'release.json'):
        raise RuntimeError('Relocated release differs from ST-02 candidate')
    validate_source(control)
    backup = root / 'backups' / batch
    if backup.exists():
        raise RuntimeError('Backup batch already exists')
    backup.mkdir(parents=True)
    restrict_private(backup)
    record(backup, 'SOURCE_READY', source=PROJECT)
    changed = False
    adopted = False
    try:
        changed = True
        old_compose('maintenance', 'up', '-d', '--pull', 'never', '--no-build', '--no-deps',
                    '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
        if control.gateway_mode() != 'MAINTENANCE':
            raise RuntimeError('Maintenance gateway not active')
        record(backup, 'GATE_CLOSED')
        old_compose('maintenance', 'stop', 'web', 'market-b', 'marketing-a', 'broker', 'namesrv', 'redis')
        rows = control.inspect()
        if any(rows[name]['State']['Running'] for name in SERVICES if name != 'mysql'):
            raise RuntimeError('Writer remains running')
        record(backup, 'WRITERS_STOPPED')
        snapshot = data_snapshot(control)
        write(backup / 'baseline.json', snapshot)
        raw_to_file('logical database dump', ['docker', '--context', 'desktop-linux', 'exec',
            PROJECT + '-mysql-1', 'sh', '-c',
            'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysqldump -uroot --single-transaction --routines --triggers --events --databases group_buy_market_b06 zj_market_b06'],
            backup / 'business.sql', timeout=900)
        control.sql('SET GLOBAL innodb_fast_shutdown=0;')
        old_compose('maintenance', 'stop', 'mysql')
        rows = control.inspect()
        if any(row['State']['Running'] for row in rows.values()):
            raise RuntimeError('Container still running at cold point')
        record(backup, 'COLD_POINT', baseline=snapshot)
        image = control.release['images']['redis']
        for volume in VOLUMES:
            archive = backup / (volume + '.tar')
            raw_to_file('cold volume ' + volume,
                ['docker', '--context', 'desktop-linux', 'run', '--rm', '--network', 'none',
                 '--read-only', '--cap-drop', 'ALL', '--cap-add', 'DAC_OVERRIDE',
                 '--mount', 'type=volume,src=' + PROJECT + '_' + volume + ',dst=/volume,readonly',
                 '--entrypoint', 'tar', image, '--numeric-owner', '-cpf', '-', '-C', '/volume', '.'],
                archive, timeout=1200)
        files = {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size}
                 for p in [backup / 'baseline.json', backup / 'business.sql',
                           *(backup / (v + '.tar') for v in VOLUMES)]}
        manifest = {'format': 1, 'project': PROJECT, 'batch': batch, 'consistentPointAtUtc': stamp(),
                    'volumes': [PROJECT + '_' + v for v in VOLUMES], 'files': files,
                    'releaseSha256': sha(control.release_path), 'restoreOverLiveVolumes': False}
        write(backup / 'manifest.json', manifest)
        write(backup / 'COMPLETE.json', {'manifestSha256': sha(backup / 'manifest.json')})
        if any(sha(backup / name) != item['sha256'] for name, item in files.items()):
            raise RuntimeError('Cold backup hash mismatch')
        record(backup, 'BACKUP_COMPLETE')
        write(root / 'state' / 'adoption.json', {'release': RELEASE, 'project': PROJECT,
            'releaseSha256': sha(control.release_path), 'backupBatch': batch,
            'backupManifestSha256': sha(backup / 'manifest.json')})
        result = control.start()
        if result['status'] != 'READY':
            raise RuntimeError('New stable controller did not reach READY')
        adopted = True
        record(backup, 'ADOPTED_READY')
    except Exception:
        if changed and not adopted:
            try:
                write(backup / 'cutover-diagnostic.json', adoption_diagnostics(control))
            except Exception:
                pass
            try:
                old_recover()
                (root / 'state' / 'adoption.json').unlink(missing_ok=True)
                record(backup, 'OLD_RECOVERED_AFTER_FAILURE')
            except Exception:
                record(backup, 'RECOVERY_REQUIRED')
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--batch', required=True)
    args = parser.parse_args()
    if not args.batch.startswith('st03_') or not args.batch.replace('_', '').isalnum():
        raise RuntimeError('Invalid backup batch')
    cutover(args.root, args.batch)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ST03_ERROR ' + str(error))
        raise SystemExit(1)
