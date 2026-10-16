"""Read-only TD-06.0 inventory of the live 443 shop and isolated 8445 candidate.

The result is a time-stamped observation, not a consistent backup or a release gate.
No raw customer/order IDs, credentials, or configuration values are written.
"""
from __future__ import annotations

import hashlib
import argparse
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

B = Path(__file__).resolve().parents[2]
A = Path('D:/Java/group-buy-market')
LEGACY = Path('D:/Java/zj-market-b-06')
TD05 = B / 'target/team-discovery/td05_20261015_01'
DOCKER = ['docker', '--context', 'desktop-linux']
SERVICES = ('mysql', 'redis', 'namesrv', 'broker', 'marketing-a', 'market-b', 'web')
PROJECTS = {'main443': 'zj-market-b06', 'candidate8445': 'zj-market-td05-20261015-01'}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def call(args: list[str], *, input_text: str | None = None) -> str:
    result = subprocess.run(args, input=input_text, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=180)
    if result.returncode:
        raise RuntimeError('Read-only baseline command failed: ' + ' '.join(args[:5]))
    return result.stdout


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def git(repo: Path, *args: str) -> str:
    return call(['git', '-C', str(repo), *args]).strip()


def mysql(project: str, sql: str) -> str:
    return call(DOCKER + ['exec', '-i', project + '-mysql-1', 'sh', '-c',
                'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --skip-column-names'],
                input_text=sql)


def config_hashes(base: Path, names: tuple[str, ...]) -> dict[str, str]:
    result = {}
    for name in names:
        path = base / name
        if not path.is_file():
            raise RuntimeError('Missing expected configuration: ' + name)
        result[name] = sha(path)
    return result


def status_snapshot(project: str) -> dict:
    groups = {
        'aTeams': ('group_buy_market_b06.ab_team', 'team_status'),
        'aOrders': ('group_buy_market_b06.ab_trade_order', 'order_status'),
        'aInbox': ('group_buy_market_b06.ab_inbox', 'processing_status'),
        'aOutbox': ('group_buy_market_b06.ab_outbox', 'status'),
        'bOrders': ('zj_market_b06.b_market_order', 'business_status'),
        'bReservations': ('zj_market_b06.b_inventory_reservation', 'state'),
        'bPayments': ('zj_market_b06.b_payment', 'funds_state'),
        'bRefunds': ('zj_market_b06.b_refund', 'funds_status'),
        'bCoordination': ('zj_market_b06.b_trade_coordination', 'run_state'),
        'bTradeWork': ('zj_market_b06.b_trade_work', 'state'),
        'bTradeInbox': ('zj_market_b06.b_trade_inbox', 'state'),
        'bTradeOutbox': ('zj_market_b06.b_trade_outbox', 'state'),
        'bReconciliation': ('zj_market_b06.b_reconciliation_task', 'state'),
        'bReconSubmission': ('zj_market_b06.b_reconciliation_submission', 'state'),
        'bRefundTask': ('zj_market_b06.b_refund_task', 'state'),
        'bRefundAttempt': ('zj_market_b06.b_refund_attempt', 'state'),
        'bSimPayment': ('zj_market_b06.b_sim_payment', 'gate'),
        'bSimRefundAttempt': ('zj_market_b06.b_sim_refund_attempt', 'state'),
    }
    sql = ['SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;',
           'START TRANSACTION WITH CONSISTENT SNAPSHOT;',
           "SELECT 'OBSERVED_UTC', DATE_FORMAT(UTC_TIMESTAMP(3),'%Y-%m-%dT%H:%i:%s.%fZ');"]
    for label, (table, column) in groups.items():
        sql.append(f"SELECT '{label}',{column},COUNT(*) FROM {table} GROUP BY {column};")
    sql += [
        "SELECT 'aWaitingDependency','total',COUNT(*) FROM group_buy_market_b06.ab_waiting_dependency;",
        "SELECT 'aExceptionPayment','total',COUNT(*) FROM group_buy_market_b06.ab_exception_payment;",
        "SELECT 'bOrderBlocks',state,COUNT(*) FROM zj_market_b06.b_order_block GROUP BY state;",
        "SELECT 'bPurchaseGuards','active',COUNT(*) FROM zj_market_b06.b_purchase_guard WHERE active_order_id IS NOT NULL;",
        "SELECT 'bChannelMoney','paidAmount',COALESCE(SUM(amount),0) FROM zj_market_b06.b_sim_payment WHERE gate='PAID';",
        "SELECT 'bChannelMoney','refundedAmount',COALESCE(SUM(refunded_amount),0) FROM zj_market_b06.b_sim_refund;",
        "SELECT 'bInventory','available',COALESCE(SUM(available),0) FROM zj_market_b06.b_inventory_account;",
        "SELECT 'bInventory','reserved',COALESCE(SUM(reserved),0) FROM zj_market_b06.b_inventory_account;",
        "SELECT 'bInventory','sold',COALESCE(SUM(sold),0) FROM zj_market_b06.b_inventory_account;",
        "SELECT 'aDueTeams','formingPastEnd',COUNT(*) FROM group_buy_market_b06.ab_team WHERE team_status='FORMING' AND valid_end_time<=UTC_TIMESTAMP(3);",
        "SELECT 'bDueWork','tradeWork',COUNT(*) FROM zj_market_b06.b_trade_work WHERE state IN ('READY','WAITING_DEPENDENCY','REVIEW_REQUIRED') AND next_attempt_ms<=UNIX_TIMESTAMP(UTC_TIMESTAMP(3))*1000;",
        'COMMIT;'
    ]
    result: dict[str, dict[str, int | str]] = {}
    for row in mysql(project, '\n'.join(sql)).splitlines():
        parts = row.split('\t')
        if len(parts) not in (2, 3):
            raise RuntimeError('Unexpected inventory row shape')
        label, key = parts[:2]
        if label == 'OBSERVED_UTC':
            result['observedAtUtc'] = key
        else:
            result.setdefault(label, {})[key] = int(parts[2]) if parts[2].lstrip('-').isdigit() else parts[2]
    return result


def obligation_snapshot(project: str) -> dict:
    """Hashed keys allow later reconciliation without publishing order or team IDs."""
    queries = {
        'aReconcilingTeams': "SELECT team_id,team_status FROM group_buy_market_b06.ab_team WHERE team_status IN ('FORMING','RECONCILING') ORDER BY team_id",
        'aPaidOrders': "SELECT out_trade_no,order_status FROM group_buy_market_b06.ab_trade_order WHERE order_status='PAID' ORDER BY out_trade_no",
        'aOutboxPending': "SELECT event_id,status FROM group_buy_market_b06.ab_outbox WHERE status<>'PUBLISHED' ORDER BY event_id",
        'aWaitingDependency': "SELECT event_id,'WAITING' FROM group_buy_market_b06.ab_waiting_dependency ORDER BY event_id",
        'bOpenOrders': "SELECT order_id,business_status FROM zj_market_b06.b_market_order WHERE business_status NOT IN ('CLOSED','GROUP_COMPLETED') ORDER BY order_id",
        'bUnsettledPayments': "SELECT payment_id,funds_state FROM zj_market_b06.b_payment WHERE funds_state NOT IN ('SUCCEEDED','UNPAID') ORDER BY payment_id",
        'bUnsettledRefunds': "SELECT refund_id,funds_status FROM zj_market_b06.b_refund WHERE funds_status<>'SUCCEEDED' ORDER BY refund_id",
        'bTradeWork': "SELECT work_id,CONCAT(kind,':',state) FROM zj_market_b06.b_trade_work WHERE state<>'DONE' ORDER BY work_id",
        'bTradeInbox': "SELECT inbox_id,state FROM zj_market_b06.b_trade_inbox WHERE state<>'DONE' ORDER BY inbox_id",
        'bTradeOutbox': "SELECT event_id,state FROM zj_market_b06.b_trade_outbox WHERE state<>'DONE' ORDER BY event_id",
        'bReconciliation': "SELECT task_id,state FROM zj_market_b06.b_reconciliation_task WHERE state<>'RESOLVED' ORDER BY task_id",
        'bRefundTask': "SELECT refund_id,state FROM zj_market_b06.b_refund_task WHERE state<>'DONE' ORDER BY refund_id",
        'bActiveBlocks': "SELECT order_id,CONCAT(kind,':',state) FROM zj_market_b06.b_order_block WHERE state='ACTIVE' ORDER BY order_id,kind",
    }
    sql = ['SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;',
           'START TRANSACTION WITH CONSISTENT SNAPSHOT;']
    for label, query in queries.items():
        sql.append(f"SELECT '{label}',q.* FROM ({query}) q;")
    sql.append('COMMIT;')
    result = {key: [] for key in queries}
    for row in mysql(project, '\n'.join(sql)).splitlines():
        label, raw_id, state = row.split('\t')
        result[label].append({'keySha256': hashlib.sha256(raw_id.encode()).hexdigest().upper(), 'state': state})
        if len(result[label]) > 1000:
            raise RuntimeError('Unbounded obligation list: ' + label)
    return result


def snapshot(project: str, expected_images: dict[str, str], config: dict[str, str]) -> dict:
    containers = json.loads(call(DOCKER + ['inspect'] + [project + '-' + s + '-1' for s in SERVICES]))
    images = {}
    for service, container in zip(SERVICES, containers):
        if container['State']['Health']['Status'] != 'healthy' or container['State']['OOMKilled']:
            raise RuntimeError(project + ' unhealthy: ' + service)
        if container['Config']['Labels'].get('com.docker.compose.project') != project:
            raise RuntimeError(project + ' ownership mismatch: ' + service)
        images[service] = container['Image']
    for service, image in expected_images.items():
        if images[service] != image:
            raise RuntimeError(project + ' image drift: ' + service)
    spec = importlib.util.spec_from_file_location('deployment', B / 'scripts/b06-deployment.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    deployment = object.__new__(module.Deployment)
    deployment.admin = lambda _label, sql: mysql(project, sql)
    grants = mysql(project, "SHOW GRANTS FOR 'a_runtime'@'%'; SHOW GRANTS FOR 'b_runtime'@'%';")
    if any(x in grants.upper() for x in ('ALTER', 'CREATE', 'DROP', 'INDEX', 'ALL PRIVILEGES')):
        raise RuntimeError(project + ' runtime DDL grant detected')
    index_rows = mysql(project, "SELECT INDEX_NAME,SEQ_IN_INDEX,COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='group_buy_market_b06' AND INDEX_NAME IN ('idx_ab_team_discovery','idx_ab_order_discovery_owner') ORDER BY INDEX_NAME,SEQ_IN_INDEX;").splitlines()
    return {'project': project, 'images': images, 'allServicesHealthy': True,
            'configSha256': config, 'schemaFingerprint': deployment.fingerprint(),
            'migrationHistorySha256': deployment.history(), 'discoveryIndexColumns': index_rows,
            'runtimeDdlGranted': False, 'business': status_snapshot(project),
            'obligations': obligation_snapshot(project)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-name', default='td06-0-baseline.json')
    name = parser.parse_args().output_name
    if not name.startswith('td06-0-baseline') or not name.endswith('.json') or '/' in name or '\\' in name:
        raise RuntimeError('Output must be a TD-06.0 baseline JSON filename')
    output = B / 'docs/tests' / name
    if output.exists():
        raise RuntimeError('TD-06.0 baseline already exists; do not overwrite observation')
    release = load(B / 'docs/team-discovery-td05-release.json')
    old = load(B / 'docs/b06-final-release.json')
    lock = load(B / 'docs/team-discovery-contract-lock.json')
    source = load(TD05 / 'a-source-hashes.json')
    if any(not (A / name).is_file() or sha(A / name) != digest for name, digest in source.items()):
        raise RuntimeError('A frozen source changed')
    if sha(TD05 / 'a-source/group-buy-market-contract/target/group-buy-market-contract-1.1.0-td.1.jar') != lock['sha256']:
        raise RuntimeError('Frozen contract changed')
    spec = importlib.util.spec_from_file_location('td05_release', B / 'docs/tests/collect-td05-release.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.digest(module.source_hashes(B)) != release['bSourceSha256']:
        raise RuntimeError('B source changed from TD-05 candidate')
    if any(git(repo, 'branch', '--show-current') != 'codex/team-discovery-td00' for repo in (A, B)):
        raise RuntimeError('Unexpected branch')
    main_config = config_hashes(LEGACY, ('.local/b06/control/state.json', '.local/b06/control/capabilities.properties',
                                         '.local/b06/runtime/a.properties', '.local/b06/runtime/b.properties',
                                         'deploy/b06/compose.yml', 'deploy/b06/config/admission-open.conf'))
    candidate_config = config_hashes(TD05, ('compose.json', 'private/config/a.properties',
                                             'private/config/b.properties', 'private/control/capabilities.properties',
                                             'private/config/admission-open.conf'))
    observed = {
        'stage': 'TD-06.0', 'status': 'READ_ONLY_BASELINE_CAPTURED',
        'capturedAtUtc': datetime.now(timezone.utc).isoformat(),
        'target': 'Daily HTTPS 443 main443; 8445 remains isolated candidate',
        'source': {'aBranch': git(A, 'branch', '--show-current'), 'aHead': git(A, 'rev-parse', 'HEAD'),
                   'bBranch': git(B, 'branch', '--show-current'), 'bHead': git(B, 'rev-parse', 'HEAD'),
                   'aFrozenSourceFileCount': len(source), 'aFrozenSourceSha256': release['aFrozenSourceSha256'],
                   'bSourceSha256AtTd05': release['bSourceSha256'],
                   'contractJarSha256': lock['sha256'], 'sourceUncommitted': True},
        'main443': snapshot(PROJECTS['main443'], {k: old['images'][v] for k, v in
                                                 [('marketing-a', 'a'), ('market-b', 'b'), ('web', 'web')]}, main_config),
        'candidate8445': snapshot(PROJECTS['candidate8445'], {k: release['images'][v]['id'] for k, v in
                                                               [('marketing-a', 'a'), ('market-b', 'b'), ('web', 'web')]}, candidate_config),
        'scope': 'Read-only live observation; rows may change after capture; no stop-write, backup, migration, switch, or trade mutation',
        'nextGate': 'TD-06.2 must quiesce all writers and make a new consistent backup of the then-current main443 volumes and data before any upgrade.'
    }
    state = load(LEGACY / '.local/b06/control/state.json')
    if observed['main443']['schemaFingerprint'] != state['schemaFingerprint'] or observed['main443']['migrationHistorySha256'] != state['migrationHistoryHash']:
        raise RuntimeError('Main 443 schema/history differs from live B-06 control state')
    if observed['candidate8445']['schemaFingerprint'] != release['aSchemaFingerprint'] or observed['candidate8445']['migrationHistorySha256'] != release['bMigrationHistorySha256']:
        raise RuntimeError('Candidate schema/history differs from TD-05 release')
    if observed['main443']['discoveryIndexColumns'] or len(observed['candidate8445']['discoveryIndexColumns']) != 10:
        raise RuntimeError('Discovery index baseline differs from expected old/new state')
    output.write_text(json.dumps(observed, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS TD-06.0 read-only baseline: ' + str(output))


if __name__ == '__main__':
    main()
