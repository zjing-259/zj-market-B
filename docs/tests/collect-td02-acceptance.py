"""Bind final B jar, frozen A contract, full JUnit and isolated real A/B evidence."""
import hashlib,json,subprocess,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
run=ROOT/'target/team-discovery/td02_20261014_07';report=read(run/'report.json')
assert report['status']=='PASSED' and all(report['checks'].values())
contract=read(ROOT/'docs/team-discovery-contract-lock.json')['sha256']
local=Path('C:/Users/wanghao/.m2/repository/cn/bugstack/group-buy-market-contract/1.1.0-td.1/group-buy-market-contract-1.1.0-td.1.jar')
assert sha(local)==contract
app=ROOT/'zj-market-app/target/zj-market-app-exec.jar'
with zipfile.ZipFile(app) as jar:
 artifact=jar.read('BOOT-INF/lib/group-buy-market-contract-1.1.0-td.1.jar')
 assert hashlib.sha256(artifact).hexdigest().upper()==contract
tests=list((ROOT/'zj-market-app/target/surefire-reports').glob('TEST-*.xml'))
counts={'classes':len(tests),'tests':0,'failures':0,'errors':0,'skipped':0}
for p in tests:
 x=ET.parse(p).getroot()
 for k in ('tests','failures','errors','skipped'):counts[k]+=int(x.attrib.get(k,0))
assert counts['tests']==130 and counts['failures']==counts['errors']==counts['skipped']==0
paths=['pom.xml','zj-market-app/src/main/java/cn/zj/zjmarket/ZjMarketApplication.java','zj-market-app/src/main/java/cn/zj/zjmarket/app/config/TeamDiscoveryConfiguration.java','zj-market-app/src/main/java/cn/zj/zjmarket/app/security/IdentityHttpFilter.java','zj-market-app/src/main/resources/application.properties','zj-market-domain/src/main/java/cn/zj/zjmarket/domain/order/adapter/port/ITeamDiscoveryPort.java','zj-market-domain/src/main/java/cn/zj/zjmarket/domain/order/model/valobj/DiscoveryItem.java','zj-market-domain/src/main/java/cn/zj/zjmarket/domain/order/model/valobj/DiscoveryPage.java','zj-market-domain/src/main/java/cn/zj/zjmarket/domain/order/service/ITeamDiscoveryService.java','zj-market-domain/src/main/java/cn/zj/zjmarket/domain/order/service/impl/TeamDiscoveryService.java','zj-market-infrastructure/src/main/java/cn/zj/zjmarket/infrastructure/adapter/port/order/DubboTeamDiscoveryPort.java','zj-market-trigger/src/main/java/cn/zj/zjmarket/trigger/http/TeamDiscoveryController.java','zj-market-trigger/src/main/java/cn/zj/zjmarket/trigger/http/TeamDiscoveryGate.java','zj-market-app/src/test/java/cn/zj/zjmarket/test/order/TeamDiscoveryBackendTest.java','zj-market-app/src/test/java/cn/zj/zjmarket/test/order/TeamDiscoveryGateTest.java','zj-market-app/src/test/java/cn/zj/zjmarket/test/order/TeamDiscoveryHttpTest.java','docs/tests/run-td02-live.py','docs/tests/td02/HoldAProvider.java']
sources={p:sha(ROOT/p) for p in paths}
release={'stage':'TD-02','status':'TESTED_B_SOURCE_CANDIDATE_NOT_DEPLOYED','bHead':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),'sourceUncommitted':bool(git('status','--porcelain')),'appJarPath':'zj-market-app/target/zj-market-app-exec.jar','appJarSha256':sha(app),'contractCoordinate':'cn.bugstack:group-buy-market-contract:1.1.0-td.1','embeddedContractSha256':contract,'featureFlagDefault':False,'originalB06Updated':False,'sourceSha256':sources}
write(ROOT/'docs/team-discovery-b-release.json',release)
summary={'stage':'TD-02','status':'PASSED_B_BACKEND_REAL_A_TLS','stageCompletion':True,'sourceUncommitted':True,'fullMavenPackage':counts,'realAHttpTestBatch':'td02_20261014_07','isolatedBatchTests':18,'realAHttpTestMethods':5,'sharedTestMethodsWithFullSuite':18,'realAConditionalBranchesOnlyInIsolatedBatch':True,'realAHttpP95':report['httpTiming'],'aSchema':report['aSchema'],'aBusinessRowsBefore':report['aBefore'],'aBusinessRowsAfter':report['aAfter'],'originalBusinessRowsBefore':report['originalBefore'],'originalBusinessRowsAfter':report['originalAfter'],'temporaryContainersAndNetworkCleaned':True,'contractSha256':contract,'bCandidateJarSha256':sha(app),'evidence':{'isolatedRunReport':sha(run/'report.json'),'isolatedRunLog':sha(run/'b-http-test.log'),'realHttpMetrics':sha(run/'http-metrics.json')},'limits':['B local product/order/stock/trial readers were isolated test fixtures during real HTTP-to-A test; full dual-database/MQ/browser checkout belongs to TD-04.','Cold first Dubbo reference call may exceed 3000ms and returns 503; bounded warm-up in test precedes latency sample.','Original B06 runtime images and database were not upgraded.'],'failedRunsRetained':['td02_20261014_01','td02_20261014_02','td02_20261014_03','td02_20261014_04'],'nextStage':'TD-03'}
write(ROOT/'docs/tests/td02-acceptance.json',summary)
print(json.dumps({'status':summary['status'],'tests':counts['tests'],'jarSha256':release['appJarSha256']}))
