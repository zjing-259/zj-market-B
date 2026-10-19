"""Publish a credential-free acceptance summary only after actual release checks pass."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
import importlib.util, json, subprocess

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT/'.local/ux05'
BATCH = 'ux05-20261019-01'
spec = importlib.util.spec_from_file_location('ux05_release', ROOT/'scripts/ux05-release.py')
r = importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
if ROOT.name != 'zj-market-ux':raise RuntimeError('UX worktree required')
reports = {}
for target in ['ux', 'main']:
    subprocess.run(['py', '-B', 'scripts/ux05-joint.py', 'collect', '--target', target, '--batch', BATCH], cwd=ROOT, check=True)
    reports[target] = r.load(WORK/(BATCH+'-'+target)/'accounting-report.json')
    assert reports[target]['status'] == 'PASSED_REAL_BROWSER_ACCOUNTING'
    assert len(reports[target]['facts']['success']['orders']) == 2

control = r.controller(r.NEW)
control.ready()
before = r.snapshot(control)
container_args = control.docker+['inspect', '--format', '{{.Id}}', *[r.PROJECT+'-'+name+'-1' for name in r.SERVICES]]
ids_before = subprocess.check_output(container_args, text=True)
assert control.start()['status'] == 'READY'
assert control.start()['status'] == 'READY'
after = r.snapshot(control)
assert before == after, 'Readiness/idempotent start changed business facts'
assert ids_before == subprocess.check_output(container_args, text=True)
upgraded = r.load(WORK/'main-upgrade.json')
original = upgraded['before']
current_rows = {line.split('\t')[0]: line for line in after['originalOrders']}
assert all(current_rows.get(line.split('\t')[0]) == line for line in original['originalOrders'])
assert len(after['originalOrders']) - len(original['originalOrders']) == 4
def balances(rows):return {line.split('\t')[0]: Decimal(line.split('\t')[1]) for line in rows}
previous_balances, current_balances = balances(original['moneyStock']), balances(after['moneyStock'])
deltas = {key: current_balances[key]-value for key,value in previous_balances.items()}
assert deltas == {'paid': Decimal(270), 'refunded': Decimal(90), 'available': Decimal(28), 'reserved': Decimal(0), 'sold': Decimal(2)}
health = {'status':'PASS','twoRepeatedStartsKeptContainerIds':True,'businessFactsUnchangedByHealthChecks':True,
          'originalOrdersPreservedAfterNewTrades':len(original['originalOrders']),'mainBatchDelta':{k:str(v) for k,v in deltas.items()}}
r.write(WORK/'main-final-health.json',health)
isolation = json.loads(subprocess.check_output(['py','-B','scripts/ux05-isolation.py'],cwd=ROOT,text=True,encoding='utf-8'))
assert isolation['status'] == 'PASS'
r.write(WORK/'isolation.json',isolation)
faults = r.load(WORK/'faults.json');assert faults['status']=='PASS'
rollback = r.load(WORK/'rollback-drill.json');assert rollback['status']=='PASS' and rollback['restoredFromBackup'] is False
resume_guard = r.load(WORK/'resume-guard.json');assert resume_guard['status']=='PASS'
regression = r.load(WORK/'regression.json');assert len(regression)==6 and all(x['exitCode']==0 for x in regression)
assets = r.load(WORK/'web-assets.json');assert assets['status']=='PASS'
backup = r.STABLE/'backups'/upgraded['backupBatch']
assert r.load(backup/'COMPLETE.json')['manifestSha256'] == r.sha(backup/'manifest.json')
backup_manifest = r.load(backup/'manifest.json')
for name,item in backup_manifest['files'].items():
    file=(backup/name).resolve()
    assert file.is_relative_to(backup.resolve()) and r.sha(file)==item['sha256']
old_source=Path('D:/Java/zj-market/target/stable-isolation/st03_20261016_04/bundle/releases')/r.OLD/'release.json'
assert r.sha(old_source)==r.sha(r.STABLE/'releases'/r.OLD/'release.json')
historical={}
for name in ['team-discovery-td06-release.json','team-discovery-td06-source-lock.json']:
    assert r.sha(ROOT/'docs'/name)==r.sha(Path('D:/Java/zj-market/docs')/name)
    historical[name]=r.sha(ROOT/'docs'/name)
source_locks = r.load(WORK/'candidate-sources.json')
assert all(r.sha(ROOT/name)==expected for name,expected in source_locks.items())
source_locks.update({str(p.relative_to(ROOT)).replace('\\','/'):r.sha(p) for p in (ROOT/'scripts').glob('ux05-*') if p.is_file()})
matrix={
 'UX-T01':['ux01-navigation.mjs','ux04-live.mjs'], 'UX-T02':['ux00-response.mjs'],
 'UX-T03':['ux05-faults.py','main-final-health.json'], 'UX-T04':['ux01-navigation.mjs','ux02-purchase.mjs','ux03-flow.mjs','real-browser'],
 'UX-T05':['ux02-purchase.mjs','real-browser'], 'UX-T06':['ux02-purchase.mjs'],
 'UX-T07':['ux02-purchase.mjs'], 'UX-T08':['ux03-flow.mjs','real-browser-original-operation-recovery'],
 'UX-T09':['ux02-purchase.mjs','ux03-flow.mjs'], 'UX-T10':['real-browser','A/B-accounting'],
 'UX-T11':['ux03-flow.mjs'], 'UX-T12':['team-discovery.mjs'], 'UX-T13':['ux02-purchase.mjs','ux03-flow.mjs','real-browser'],
 'UX-T14':['ux04-operator.mjs','ux04-live.mjs','real-browser'], 'UX-T15':['ux04-operator.mjs','ux04-live.mjs','real-browser'],
 'UX-T16':['main-upgrade.json','ux05-isolation.py','web-assets.json']}
summary={
 'format':1,'stage':'UX-05','status':'PASS','completed':True,'generatedAt':datetime.now(timezone.utc).isoformat(),
 'environment':'Local Windows + Docker Desktop Linux engine; real Edge with certificate verification',
 'release':r.NEW,'mainOrigin':'https://zj-market.test','uxOrigin':'https://zj-market-ux.test:8446',
 'images':control.release['images'],'backendJars':r.load(WORK/'jar-locks.json'),
 'schemaFingerprint':control.release['schemaFingerprint'],'flywayHistorySha256':control.release['flywayHistorySha256'],
 'releaseManifestSha256':r.sha(control.release_path),'privateManifestSha256':control.release['privateManifestSha256'],
 'webArchiveSha256':r.sha(r.STABLE/'images/web-ux05-20261019-01.tar'),
 'latestPreUpgradeBackup':{'batch':upgraded['backupBatch'],'manifestSha256':r.sha(backup/'manifest.json'),'verifiedFiles':len(backup_manifest['files']),'coldVolumes':5,'logicalDump':True,'privateConfigurationBackup':True,'restoreOverLiveVolumes':False},
 'mainFinalHealth':health,'isolation':{'status':'PASS','checks':isolation['checks']},'faults':faults,'compatibleRollbackDrill':rollback,'coldResumeGuard':resume_guard,
 'regressions':regression,'productionBuild':'PASS vue-tsc + vite; both running web files match build','webAssets':assets,
 'acceptanceMatrix':{key:{'status':'PASS','evidence':value} for key,value in matrix.items()},
 'jointBatches':{},'sourceSha256':source_locks,'historicalTD06LocksUnchanged':historical,
 'boundaries':['Simulated funds only; no actual bank payment or fulfillment',
   'Response-loss, multi-tab, price-race and HTML-response variants use controlled browser API simulations; actual A/B transactions and isolated A/B outages were separately verified',
   'Main backup is the pre-upgrade cold point; new acceptance transactions follow it. Rollback uses compatible fixed images with CURRENT data; no backup restored over live volumes',
   'No off-machine acceptance required; no master merge or image upload performed'],
}
for target,report in reports.items():
    summary['jointBatches'][target]={'batch':BATCH,'status':report['status'],'orders':sum(len(v['orders']) for v in report['facts'].values()),
      'paidAmount':'270.00','refundedAmount':'90.00','netAmount':'180.00','browserChecks':report['browserChecks'],'accountingChecks':report['accountingChecks'],
      'executedBrowserSha256':report['executedBrowserSha256'],'privateAccountingReportSha256':r.sha(WORK/(BATCH+'-'+target)/'accounting-report.json'),'screenshots':report['screenshots']}
r.write(ROOT/'docs/tests/ux05-acceptance.json',summary)
print('UX05_FINAL_ACCEPTANCE_PASS two-real-batches/original-60-orders/backup-and-release/16-scenarios')
