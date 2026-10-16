"""Consolidate the TD-04 real-stack and earlier contract/query/UI evidence."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,subprocess,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
A=Path('D:/Java/group-buy-market')
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);a=p.parse_args()
 if not re.fullmatch(r'td04_[0-9]{8}_[0-9]{2}',a.run_name):raise ValueError('Invalid batch')
 work=ROOT/'target/team-discovery'/a.run_name
 def read(path):return json.loads(path.read_text())
 sources={
  'td01':'docs/tests/td01-acceptance.json','td02':'docs/tests/td02-acceptance.json',
  'browser':'browser05/browser-report.json','browserAccounting':'browser05/accounting-report.json',
  'race':'race-race-report.json','raceAccounting':'race-accounting-report.json',
  'tabs':'race-tabs-report.json','tabsAccounting':'tabs-accounting-report.json',
  'readonly':'readonly-accounting-report.json','unknown':'unknown-accounting-report.json',
  'expirySubmission':'expiry-race-accounting-02-report.json','latePayment':'late-payment-accounting-report.json',
  'oldA':'old-a-compatibility-report.json','flagOff':'race-disabled-report.json',
  'aOutage':'race-outage-report.json','aRecovered':'race-recovered-report.json',
 }
 reports={key:read((ROOT if value.startswith('docs/') else work)/value) for key,value in sources.items()}
 assert reports['td01']['stageCompletion'] and reports['td02']['stageCompletion']
 assert reports['td01']['status'].startswith('PASSED_') and reports['td02']['status'].startswith('PASSED_')
 for key in sources.keys()-{'td01','td02'}:assert reports[key]['status'].startswith('PASSED'),key
 assert not reports['browserAccounting']['stageCompletion'] and not reports['raceAccounting']['stageCompletion']
 assert not reports['readonly']['stageCompletion'] and not reports['unknown']['stageCompletion']
 assert reports['latePayment']['aTeam']['status']=='COMPLETED'
 assert reports['expirySubmission']['aTeam']['status']=='FAILED'
 prepared=read(work/'prepare-report.json')
 assert prepared['status']=='READY' and 'sealed-source-backup-hashes' in prepared['checks']
 for key,file in {'aJar':A/'group-buy-market-app/target/group-buy-market-app.jar','bJar':ROOT/'zj-market-app/target/zj-market-app-exec.jar','frontendIndex':ROOT/'frontend/dist/index.html'}.items():
  assert hashlib.sha256(file.read_bytes()).hexdigest()==prepared['sourceSha256'][key],key
 blog=(work/'b-tests.log').read_text(errors='replace')
 assert '[INFO] BUILD SUCCESS' in blog and 'Tests run: 129, Failures: 0, Errors: 0, Skipped: 0' in blog
 frontend=(work/'frontend-tests.log').read_text(errors='replace')
 assert 'pass 6' in frontend and 'fail 0' in frontend
 assert 'built in' in (work/'frontend-build.log').read_text(errors='replace')
 surefire=ET.parse(A/'group-buy-market-app/target/surefire-reports/TEST-cn.bugstack.test.v2.V2TeamDiscoveryCursorTest.xml').getroot()
 assert surefire.attrib['tests']=='4' and surefire.attrib['failures']==surefire.attrib['errors']=='0'
 docker=['docker','--context','desktop-linux'];project='zj-market-'+a.run_name.replace('_','-')
 services=['mysql','redis','namesrv','broker','marketing-a','market-b','web']
 names=[prefix+'-'+s+'-1' for prefix in (project,'zj-market-b06') for s in services]
 containers=json.loads(subprocess.check_output(docker+['inspect']+names,text=True))
 assert all(c['State']['Health']['Status']=='healthy' and not c['State']['OOMKilled'] for c in containers)
 currentA=next(c for c in containers if c['Name'].strip('/')==project+'-marketing-a-1')
 assert any(m['Destination']=='/app/app.jar' and str(A/'group-buy-market-app/target/group-buy-market-app.jar').lower()==m['Source'].lower() for m in currentA['Mounts'])
 assert 'b.team-discovery.enabled=true' in (work/'private/config/b.properties').read_text()
 assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='codex/team-discovery-td00'
 assert subprocess.check_output(['git','branch','--show-current'],cwd=A,text=True).strip()=='codex/team-discovery-td00'
 matrix={
  'TD-T01':['td01:A accepted payment and vacancy test','browser:paid team discoverable'],
  'TD-T02':['td01:A owner, case variant and cancelled history test','browser:other buyer order hidden'],
  'TD-T03':['td01:A reserved-full query test','race:only one last slot'],
  'TD-T04':['td01:A expired/RECONCILING/COMPLETED/FAILED filtering','browser:natural expiry'],
  'TD-T05':['td01:A source/channel/activity/goods/qualification filter','browser:operator and buyer permissions'],
  'TD-T06':['td01:A tied cursor and scope tests','td02:B invalid parameter HTTP'],
  'TD-T07':['td01:A page context recheck','td02:B product change after RPC','frontend:pagination 409 and stale product response'],
  'TD-T08':['td02:B auth/expired/no-role/no-store HTTP','browser:cross-user/order/foreign origin'],
  'TD-T09':['browser:real product-page JOIN and two paid orders','browserAccounting:A/B/channel/stock'],
  'TD-T10':['race:concurrent last slot no alternate team','raceAccounting:quota/funds/stock'],
  'TD-T11':['tabs:two independent sessions one active order','tabsAccounting:one A order and unique stock release','unknown:same-key replay after restart','browser:reload no writes'],
  'TD-T12':['unknown:response body lost after accepted headers','unknown:B restart original team and one release'],
  'TD-T13':['aOutage:real A stop 503','td02:TLS/invalid upstream unit and old A 503'],
  'TD-T14':['expirySubmission:accepted result intent but channel unpaid and first refunded','latePayment:actual channel paid before deadline, A completed after deadline'],
  'TD-T15':['readonly:25 real HTTPS GETs, 8 A/B trade table fingerprints unchanged'],
  'TD-T16':['frontend:6 Edge tests including pause, 5-minute stop, stale responses and 429','browser:real mobile/reload'],
  'TD-T17':['oldA:current B with sealed old A explicit 503 and restored','flagOff:route absent, original trial and auth intact'],
  'TD-T18':['browser:natural paid-team expiry/refund','browserAccounting:A/B/channel full refund and unique release'],
 }
 assert len(matrix)==18 and all(matrix.values())
 sha=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()
 evidence={key:{'path':value,'sha256':sha((ROOT if value.startswith('docs/') else work)/value)} for key,value in sources.items()}
 evidence['bTests']={'path':'target/team-discovery/'+a.run_name+'/b-tests.log','sha256':sha(work/'b-tests.log')}
 evidence['frontendTests']={'path':'target/team-discovery/'+a.run_name+'/frontend-tests.log','sha256':sha(work/'frontend-tests.log')}
 report={'stage':'TD-04','status':'PASSED_REAL_JOINT_FAULT_ACCEPTANCE','stageCompletion':True,'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runName':a.run_name,'scope':'Windows isolated clone: real A/B MySQL, Redis, RocketMQ, strict TLS Edge; simulated channel money only; original B-06 unchanged','matrix':matrix,'checks':{'td01QueryTests':69,'td02BackendTests':130,'td04BRegressionTests':129,'aCursorTests':4,'frontendEdgeTests':6,'realBrowserChecks':len(reports['browser']['checks']),'realDiscoveryGetsWithoutTradeWrites':reports['readonly']['requests'],'originalB06HealthyServices':7,'isolatedHealthyServices':7,'latePaymentChannelBeforeDeadline':True,'aTeamCompletedAfterDeadline':True,'mixedOldAAndFlagOff':True},'evidence':evidence,'sourceUncommitted':True,'nextStage':'TD-05 container delivery'}
 (ROOT/'docs/tests/td04-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('PASS TD04 18-case real joint acceptance')
if __name__=='__main__':main()
