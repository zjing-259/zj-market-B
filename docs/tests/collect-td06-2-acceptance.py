"""Redacted TD-06.2 evidence from the actual 443 project after release/restart."""
from __future__ import annotations

import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

B = Path(__file__).resolve().parents[2]
OLD = Path('D:/Java/zj-market-b-06')
WORK = B / 'target/team-discovery/td06_2_main_20261015_01'
OUT = B / 'docs/tests/td06-2-acceptance.json'
PROJECT = 'zj-market-b06'
DOCKER = ['docker', '--context', 'desktop-linux']


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def run(args: list[str]) -> str:
    result = subprocess.run([str(value) for value in args], capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=180)
    if result.returncode:
        raise RuntimeError('Evidence command failed: ' + ' '.join(str(x) for x in args[:5]))
    return result.stdout


def module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    item = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item)
    return item


def main() -> None:
    if OUT.exists():
        raise RuntimeError('Evidence file is immutable; select a new batch name')
    td = module(B / 'scripts/td06-main-release.py', 'td062_release')
    baseline = module(B / 'docs/tests/collect-td06-baseline.py', 'td06_baseline')
    record = load(WORK / 'release.json')
    backup = load(OLD / '.local/b06/backups/b066-td062-20261015-03/progress.json')
    old = load(B / 'docs/tests/td06-0-baseline-final.json')['main443']
    if record['status'] != 'RESTARTED_443' or backup['status'] != 'BACKUP_COMPLETE':
        raise RuntimeError('Release or consistent backup is incomplete')
    required_events = ('INDEXES_APPLIED', 'NEW_STACK_MAINTENANCE_DISCOVERY_OFF',
                       'REAL_SIGNED_TLS_RPC_READY', 'OFF_443_AND_OLD_FLOW_READY',
                       'ENABLED_443', 'OLD_PACKAGE_FALLBACK_VERIFIED',
                       'RE_ENABLED_443_AFTER_FALLBACK', 'STOPPED', 'RESTARTED_443')
    events = [event['event'] for event in record['events']]
    if not all(name in events for name in required_events):
        raise RuntimeError('Missing required release gate')
    current_images = td.containers({'marketing-a': record['images']['a'],
                                    'market-b': record['images']['b'],
                                    'web': record['images']['web']})
    td.verify_schema(True)
    td.public_gate('on')
    td.old_ready('ready')
    volume_rows = json.loads(run(DOCKER + ['volume', 'inspect'] +
                                 [PROJECT + '_' + suffix for suffix in
                                  ('mysql-data', 'redis-data', 'broker-store', 'broker-logs', 'namesrv-logs')]))
    for row in volume_rows:
        labels = row.get('Labels') or {}
        if labels.get('com.docker.compose.project') != PROJECT or not row['Name'].startswith(PROJECT + '_'):
            raise RuntimeError('Main volume ownership changed')
    business = baseline.status_snapshot(PROJECT)
    obligations = baseline.obligation_snapshot(PROJECT)
    retained = {}
    for category, rows in old['obligations'].items():
        keys_before = {value['keySha256'] for value in rows}
        keys_now = {value['keySha256'] for value in obligations[category]}
        missing = keys_before - keys_now
        if missing:
            raise RuntimeError('Original obligation missing: ' + category)
        retained[category] = {'before': len(rows), 'after': len(obligations[category]),
                              'originalKeysMissing': 0}
    if business['bChannelMoney'] != old['business']['bChannelMoney']:
        raise RuntimeError('Original channel money changed during package release')
    if business['bInventory'] != old['business']['bInventory']:
        raise RuntimeError('Original inventory balance changed during package release')
    if td.sha(B / 'frontend/src/services/team-discovery.ts') != load(B / 'docs/tests/td06-1-acceptance-verified.json')['sourceSha256']['frontend/src/services/team-discovery.ts']:
        raise RuntimeError('3/10 pagination source drift')
    report = {'stage': 'TD-06.2', 'status': 'PASSED_MAIN_443_RELEASE',
              'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
              'project': PROJECT, 'backupBatch': record['backup'],
              'backupConsistentPointAtUtc': record['consistentPointAt'],
              'backupCompleteAndOriginalRecovered': True,
              'originalVolumesRetained': sorted(row['Name'] for row in volume_rows),
              'images': {name: current_images[name] for name in ('marketing-a', 'market-b', 'web')},
              'schemaFingerprint': record['newSchema'],
              'bMigrationHistorySha256': record['bMigrationHistory'],
              'discoveryIndexColumns': td.index_state(),
              'runtimeDdlGranted': False, 'releaseEvents': required_events,
              'realSignedTlsRpcBeforeEnable': True,
              'featureOffAndOldPackageFallbackVerified': True,
              'controlledStopStartVerified': True,
              'strictTlsHttps443AndOldTrialVerified': True,
              'mainChannelMoney': business['bChannelMoney'],
              'mainInventory': business['bInventory'],
              'obligationRetention': retained,
              'aReconcilingNewFactsAfterRelease': retained['aReconcilingTeams']['after'] - retained['aReconcilingTeams']['before'],
              'scope': 'Windows Docker main443; TD-06.3 browser JOIN/payment/refund acceptance remains separate',
              'gitPublished': False, 'registryPublished': False, 'linuxValidated': False}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS TD-06.2 main 443 release and original obligations retained')


if __name__ == '__main__':
    main()
