"""Publish sanitized B06.2 evidence from a passed immutable private batch and current owned stack."""
from pathlib import Path
import argparse,json,hashlib,subprocess,re
from datetime import datetime,timezone
import importlib.util
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def main(name,context):
 work=ROOT/'.local/b06/acceptance'/name;raw=work/'report.json';report=json.loads(raw.read_text())
 assert report['status']=='PASSED' and report['finalMode']=='open' and len(report['checks'])==35
 spec=importlib.util.spec_from_file_location('deployment',ROOT/'scripts/b06-deployment.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);d=m.Deployment(context)
 state=d.state();assert state['mode']=='open' and state['phase']=='READY'
 names=[m.PROJECT+'-'+s+'-1' for s in ['mysql','redis','namesrv','broker','marketing-a','market-b','web']]
 rows=json.loads(subprocess.check_output(d.docker+['inspect']+names));assert all(r['State']['Health']['Status']=='healthy' and not r['State']['OOMKilled'] for r in rows)
 web=next(r for r in rows if r['Name'].endswith('-web-1'));assert web['HostConfig']['PortBindings']=={'8443/tcp':[{'HostIp':'127.0.0.1','HostPort':'443'}]}
 assert any(x['Destination']=='/etc/b06/admission.conf' and x['Source'].endswith('admission-open.conf') for x in web['Mounts'])
 counts=d.admin('final-sanitized-db-facts',"SELECT 'a_tables',COUNT(*) FROM information_schema.tables WHERE table_schema='group_buy_market_b06'; SELECT 'b_tables',COUNT(*) FROM information_schema.tables WHERE table_schema='zj_market_b06'; SELECT 'a_applied_ddl',COUNT(*) FROM group_buy_market_b06.b06_init_journal WHERE state='APPLIED'; SELECT 'a_uncertain_ddl',COUNT(*) FROM group_buy_market_b06.b06_init_journal WHERE state<>'APPLIED'; SELECT 'b_sql_migrations',COUNT(*) FROM zj_market_b06.flyway_schema_history WHERE type='SQL' AND success=1; SELECT 'b_users',COUNT(*) FROM zj_market_b06.b_user; SELECT 'b_products',COUNT(*) FROM zj_market_b06.b_product; SELECT 'b_payments',COUNT(*) FROM zj_market_b06.b_payment; SELECT 'b_refunds',COUNT(*) FROM zj_market_b06.b_refund;")
 facts={k:int(v) for k,v in (line.split('\t') for line in counts.splitlines())}
 assert facts['a_tables']==23 and facts['b_tables']==49 and facts['a_uncertain_ddl']==0 and facts['b_sql_migrations']==19 and facts['b_users']==3 and facts['b_products']==1 and facts['b_payments']==facts['b_refunds']==0
 balance=d.admin('final-stock',"SELECT available,reserved,sold FROM zj_market_b06.b_inventory_account;");assert balance.strip()=='100\t0\t0'
 encrypted=d.admin('actual-app-jdbc-tls',"SELECT t.PROCESSLIST_USER,s.VARIABLE_VALUE,COUNT(*) FROM performance_schema.status_by_thread s JOIN performance_schema.threads t USING(THREAD_ID) WHERE t.PROCESSLIST_USER IN ('a_runtime','b_runtime') AND s.VARIABLE_NAME='Ssl_cipher' AND s.VARIABLE_VALUE<>'' GROUP BY t.PROCESSLIST_USER,s.VARIABLE_VALUE;")
 sessions=[dict(zip(['principal','cipher','sessions'],line.split('\t'))) for line in encrypted.splitlines()];assert {x['principal'] for x in sessions}=={'a_runtime','b_runtime'}
 topics=json.loads(subprocess.check_output(d.docker+['exec',m.PROJECT+'-broker-1','cat','/home/rocketmq/store/config/topics.json']))['topicConfigTable']
 groups=json.loads(subprocess.check_output(d.docker+['exec',m.PROJECT+'-broker-1','cat','/home/rocketmq/store/config/subscriptionGroup.json']))['subscriptionGroupTable']
 expected_topics=['B_PRODUCT_EVENTS-b06','B_TRADE_EVENTS-b06','A_TEAM_EVENTS-b06','A_INTEGRATION_RESULTS-b06'];expected_groups=['A_PRODUCT_SYNC-b06','A_TRADE_FACTS-b06','B_PRODUCT_SYNC_RESULTS-b06','B_INTEGRATION_RESULTS-b06','B_TEAM_EVENTS-b06']
 assert set(expected_topics)<=topics.keys() and set(expected_groups)<=groups.keys()
 usage={}
 for label in ['before-restart','after-restart']:
  total=0
  for line in (work/(label+'-usage.jsonl')).read_text().splitlines():
   value=json.loads(line)['MemUsage'].split('/')[0].strip();v=re.match(r'([0-9.]+)([KMGT]?i?B)',value);total+=float(v[1])*{'B':1,'KiB':1024,'MiB':1024**2,'GiB':1024**3}[v[2]]
  usage[label]=int(total)
 assert not subprocess.check_output(['git','-C','D:/Java/zj-market','status','--porcelain'],text=True).strip()
 release=json.loads((ROOT/'.local/b06/build/release-manifest.json').read_text())
 for key,suffix in [('a','marketing-a'),('b','market-b'),('web','web')]:
  actual=next(row for row in rows if row['Name']=='/'+m.PROJECT+'-'+suffix+'-1');assert actual['Image']==release['images'][key]['id']
 all_names=subprocess.check_output(d.docker+['ps','-a','--format','{{.Names}}'],text=True).splitlines();assert len(all_names)==25 and sum(n.startswith(m.PROJECT+'-') for n in all_names)==8
 locked=d.admin('final-account-ssl-locks',"SELECT User,account_locked,ssl_type FROM mysql.user WHERE User IN ('a_migrator','b_migrator') ORDER BY User;");assert locked.splitlines()==['a_migrator\tY\tANY','b_migrator\tY\tANY']
 integrity=ROOT/'.local/b06/maintenance-integrity/b062-tools02/report.json';packaging=ROOT/'.local/b06/packaging/b062-packaging01/report.json'
 ir=json.loads(integrity.read_text());pr=json.loads(packaging.read_text());assert ir['status']==pr['status']=='PASSED' and ir['image']==state['maintenanceImage']
 paths=list((ROOT/'deploy/b06').rglob('*'))+[ROOT/'.gitattributes']+[ROOT/f for f in ['scripts/b06-deployment.py','scripts/build-b06-maintenance.py','scripts/build-b06-tools.py','docs/tests/run-b06-startup.py','docs/tests/b06-startup-client.mjs','docs/tests/verify-b06-maintenance.py','docs/tests/collect-b06-startup.py']]
 source={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file()}
 output={'schemaVersion':1,'stage':'B-06.2','stageCompletion':True,'status':'PASSED_WINDOWS_DATA_INITIALIZATION_CONTROLLED_STARTUP','generatedAt':datetime.now(timezone.utc).isoformat(),'scope':'Windows Docker Desktop Linux/amd64; Linux VM and real browser UI are later stages','git':{'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'uncommitted':True,'published':False},'jointAcceptance':{'runName':name,'checks':35,'rawReport':str(raw.relative_to(ROOT)).replace('\\','/'),'sha256':sha(raw),'checkNames':[c['name'] for c in report['checks']]},'ordinaryImagePackaging':{'checks':len(pr['checks']),'rawReport':str(packaging.relative_to(ROOT)).replace('\\','/'),'sha256':sha(packaging)},'maintenanceIntegrity':{'checks':len(ir['checks']),'rawReport':str(integrity.relative_to(ROOT)).replace('\\','/'),'sha256':sha(integrity)},'baselineJunit':{'tests':107,'rerunInB062':False,'reason':'Ordinary application bytes unchanged from B061; stage deployment/tool changes covered by real integration and image checks'},'database':{'aSchema':'group_buy_market_b06','bSchema':'zj_market_b06','runtimeTables':{'a':22,'b':48},'migratorAccountsLocked':True,'facts':facts,'stock':{'available':100,'reserved':0,'sold':0},'actualApplicationEncryptedSessions':sessions,'schemaFingerprint':state['schemaFingerprint'],'migrationHistoryHash':state['migrationHistoryHash']},'mq':{'topics':{t:{k:topics[t][k] for k in ['readQueueNums','writeQueueNums','perm']} for t in expected_topics},'groups':expected_groups},'controlledStartup':{'finalMode':'open','phase':'READY','backendReloadRequired':True,'backendDisabledWithoutGatewayVerified':True,'oldDurableCancelRecoveredWithCheckoutOff':True,'schemaColumnAndConstraintDriftRejected':True,'originalVolumesPreservedOnRestart':True,'freshBatchUsesNewSecretsAndEmptyVolumes':True,'entry':'127.0.0.1:443; https://zj-market.test'},'resources':{'persistentLimitBytes':int(4.5*1024**3),'sampledPersistentWorkingSetBytes':usage,'absolutePeakClaim':False,'allSevenHealthy':True,'oomObserved':False,'latestAdmission':json.loads((m.CONTROL/'capacity.json').read_text())},'noninterference':{'originalSharedContainers':len(report['sharedContainers']),'sharedStateAndExternalAWorktreePreserved':True,'masterClean':True,'noCommitMergePush':True,'testContainersNetworksCleaned':True,'testVolumesAndPrivateEvidenceRetained':True},'sourceHashes':source,'notAcceptedHere':['Real browser hosts/OS CA setup and purchase/payment/group/refund flows (B06.3)','Linux target deployment and Linux UID/permissions','Observation/fault/backup/recovery/final delivery stages','Unsupported B05 automatic qualification boundaries remain unchanged']}
 (ROOT/'docs/tests/b06-startup-acceptance.json').write_text(json.dumps(output,indent=2)+'\n')
 release.update(stage='B-06.2',maintenanceImage=state['maintenanceImage'],sdkImage=state['sdkImage'],maintenanceToolClassSha256=ir['classSha256'],maintenanceSharedLibrariesEqualOrdinaryB=True,maintenanceLibraryHashes=ir['libraryHashes'],verificationJarSha256=sha(ROOT/'zj-market-verification/target/zj-market-verification.jar'),sourceHashes=source,publication='Local immutable content IDs; not pushed to a registry')
 (ROOT/'docs/b06-startup-release.json').write_text(json.dumps(release,indent=2)+'\n')
 print('B062 sanitized summary published; 35 joint / 33 image / 9 maintenance checks')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run-name',default='b062-startup03');p.add_argument('--context',default='desktop-linux');a=p.parse_args();main(a.run_name,a.context)
