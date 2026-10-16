"""Freeze the TD-06.1 preparation result without copying private demo credentials."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / 'target/team-discovery/td06_demo_20261015_03'
OUT = ROOT / 'docs/tests/td06-1-acceptance-verified.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


if OUT.exists():
    raise RuntimeError('Acceptance is immutable; use a new artifact for later rechecks')
demo = json.loads((DEMO / 'demo-report.json').read_text(encoding='utf-8'))
failed = json.loads((DEMO / 'demo-report-failed.json').read_text(encoding='utf-8'))
if demo['status'] != 'PASSED_CANDIDATE_DEMO_READY' or failed['status'] != 'FAILED':
    raise RuntimeError('Demo result or preserved failure missing')
checks = set(demo['checks'])
required = {'candidate-owner-image-schema-rpc-ready', 'distinct-operator-created-product',
            'isolated-inventory-inbound', 'candidate-only-hour-long-activity',
            'resume-original-order-id', 'buyer-paid-and-A-accepted',
            'second-buyer-discovers-same-team-without-share-link',
            'second-buyer-can-enter-original-JOIN'}
if not required <= checks:
    raise RuntimeError('Demo acceptance incomplete')
sources = ['scripts/open-team-discovery-browser.ps1', 'scripts/td06-environment.py',
           'docs/tests/prepare-td06-demo.mjs', 'docs/tests/verify-td06-demo.py',
           'frontend/src/services/team-discovery.ts', 'frontend/tests/team-discovery.mjs',
           'docs/tests/test-td06-environment.py']
report = {
    'stage': 'TD-06.1', 'status': 'PASSED_CANDIDATE_ENTRY_AND_DEMO_PREPARATION',
    'stageCompletion': True, 'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
    'mainTarget': 'https://zj-market.test', 'candidateTarget': 'https://zj-market.test:8445',
    'checks': {'main443ReadyAfterCandidateRestart': True, 'candidate8445ReadyAfterRestart': True,
               'candidateOwnedStopStart': True, 'candidateVolumesRetained': True,
               'frontendBuild': True, 'frontendEdgeTests': 6,
               'candidateDemoPaidAndAcceptedByA': True, 'secondBuyerSawExactTeam': True,
               'candidateDiscoveryIndexesAndSchemaGate': True,
               'negativeOwnershipConfigGates': 5, 'failClosedStartTests': 1},
    'demo': {'batch': demo['batch'], 'goodsId': demo['goodsId'], 'teamId': demo['teamId'],
             'activityId': demo['activityId'], 'teamExpiresAtUtc': demo['teamExpiresAt'],
             'reportSha256': sha(DEMO / 'demo-report.json'),
             'preservedFailedAttemptSha256': sha(DEMO / 'demo-report-failed.json')},
    'earlierFailedBatches': {
        'td06_demo_20261015_01': sha(ROOT / 'target/team-discovery/td06_demo_20261015_01/demo-report.json'),
        'td06_demo_20261015_02': sha(ROOT / 'target/team-discovery/td06_demo_20261015_02/demo-report.json')},
    'sourceSha256': {name: sha(ROOT / name) for name in sources},
    'td06ZeroBaselineSha256': sha(ROOT / 'docs/tests/td06-0-baseline-final.json'),
    'scope': 'Windows Docker isolated candidate; demo uses simulated payment; 443 remains old B-06',
    'runtimeNote': 'TD-05 candidate web image still has old 3-item continuation; TD-06.1 source/test use 3 then 10. New web image belongs to TD-06.2.',
    'sourceProvenance': 'Original failed and resumed demo script hashes remain in private reports. Current script additionally clears the historical error field on a successful resume; no business flow was rerun after that edit.',
    'gitPublished': False, 'registryPublished': False,
}
text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
private = ROOT / 'target/team-discovery/td05_20261015_01/private'
values = json.loads((private / 'runtime/private/values.json').read_text(encoding='utf-8'))
accounts = json.loads((private / 'control/demo-accounts.json').read_text(encoding='utf-8'))
if any(str(value) in text for value in values.values()) or any(item['password'] in text for item in accounts.values()):
    raise RuntimeError('Private value in acceptance result')
if 'PRIVATE KEY' in text:
    raise RuntimeError('Private key in acceptance result')
OUT.write_text(text, encoding='utf-8')
print('PASS TD-06.1 public acceptance')
