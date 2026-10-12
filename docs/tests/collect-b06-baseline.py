"""Read-only B-06 source/build inventory; never connects to services or reads secrets."""
import argparse, hashlib, io, json, subprocess, xml.etree.ElementTree as ET, zipfile
from pathlib import Path

def sha(data): return hashlib.sha256(data).hexdigest().upper()
def git(root, *args): return subprocess.check_output(['git', '-C', str(root), *args], text=True, encoding='utf-8').strip()
def artifact(path): return {'path': str(path), 'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}

parser = argparse.ArgumentParser()
parser.add_argument('--a-root', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
assert git(root, 'branch', '--show-current') == 'b-06', 'Run in B-06 worktree'
assert not args.output.exists(), 'Use a fresh output filename; preserve previous evidence'
tracked = git(root, 'ls-files').splitlines()
docs = [{'path': p, 'sha256': sha((root/p).read_bytes()), 'bytes': (root/p).stat().st_size} for p in tracked if p.startswith('docs/')]
source_changes = [p for p in git(root, 'diff', 'HEAD', '--name-only').splitlines() if not p.startswith('docs/')]
assert not source_changes, source_changes
tests = {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
reports = sorted(root.glob('*/target/surefire-reports/TEST-*.xml'))
assert reports, 'Build and test this worktree first'
for p in reports:
    suite = ET.parse(p).getroot()
    for key in tests: tests[key] += int(suite.get(key, '0'))
assert tests['tests'] == 106 and not any(tests[k] for k in ('failures','errors','skipped')), tests
bjar = root/'zj-market-app/target/zj-market-app-exec.jar'
ajar = args.a_root/'group-buy-market-app/target/group-buy-market-app.jar'
with zipfile.ZipFile(bjar) as z:
    names = z.namelist()
    libs = [p for p in names if p.startswith('BOOT-INF/lib/')]
    assert not any('verification' in p or 'flyway' in p for p in libs)
    assert int.from_bytes(z.read('BOOT-INF/classes/cn/zj/zjmarket/ZjMarketApplication.class')[6:8], 'big') == 65
    contract_name = next(p for p in libs if 'group-buy-market-contract-' in p)
    contract = z.read(contract_name)
    with zipfile.ZipFile(io.BytesIO(contract)) as cz:
        assert all(int.from_bytes(cz.read(p)[6:8], 'big') == 52 for p in cz.namelist() if p.endswith('.class'))
with zipfile.ZipFile(ajar) as z:
    acontract = z.read(next(p for p in z.namelist() if p.startswith('BOOT-INF/lib/group-buy-market-contract-')))
assert contract == acontract, 'A/B embedded contracts differ'
migrations = []
for p in sorted(root.glob('zj-market-infrastructure/src/main/resources/db/migration/*.sql')):
    rel = p.relative_to(root).as_posix()
    original = subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:'+rel])
    # Git checkout may normalize text line endings; compare canonical LF bytes.
    assert original.replace(b'\r\n', b'\n') == p.read_bytes().replace(b'\r\n', b'\n')
    migrations.append(artifact(p))
report = {
 'schemaVersion': 1, 'stage': 'B-06.0', 'date': '2026-10-11',
 'status': 'PARTIAL_ENVIRONMENT_PENDING',
 'sourceBuildChecks': 'PASSED', 'worktree': str(root), 'branch': 'b-06', 'head': git(root,'rev-parse','HEAD'),
 'tests': tests, 'sourceChanges': source_changes,
 'artifacts': [artifact(bjar), artifact(root/'zj-market-verification/target/zj-market-verification.jar'), artifact(ajar), artifact(args.a_root/'docs/ab-api-contract.md')],
 'embeddedContractSha256': sha(contract), 'contractBytecodeMajor': 52, 'bBytecodeMajor': 65,
 'ordinaryJarExcludesVerificationAndFlyway': True,
 'frontendArtifacts': [artifact(p) for p in sorted((root/'frontend/dist').rglob('*')) if p.is_file()],
 'migrationsUnchangedFromHead': True, 'migrations': migrations,
 'persistentDocumentInventory': docs,
 'aHead': git(args.a_root,'rev-parse','HEAD'), 'aStatus': git(args.a_root,'status','--short').splitlines(),
 'linuxVm': {'status':'NOT_PREPARED', 'source':'User reply 2026-10-11'},
 'notVerified': ['Linux resources/network/SSH/clock','container images and TLS/ACL','fresh database schema and runtime grants','live A/B/MQ business flows','deployment faults and backup/restore'],
 'scope': 'Local source/build inspection only; no database/RPC/MQ calls, no VM provisioning, no secret collection.'
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'status': report['status'], 'checks': report['sourceBuildChecks'], 'tests': tests, 'output':str(args.output)}, ensure_ascii=False))
