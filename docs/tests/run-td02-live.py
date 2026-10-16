"""Run B HTTP against the already-tested A provider on isolated TD01 data.

Only labeled TD02 containers/network are created and removed. Existing TD01 A
schema is snapshotted before/after and used read-only; no original B06 changes.
"""
import argparse,hashlib,importlib.util,json,os,re,subprocess,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
A=Path('D:/Java/group-buy-market')
DOCKER=['docker','--context','desktop-linux']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def cmd(argv,timeout=180,env=None):
 r=subprocess.run([str(x) for x in argv],capture_output=True,text=True,timeout=timeout,env=env)
 if r.returncode:raise RuntimeError('Command failed: '+str(argv[:4])+' (details in private or ignored logs)')
 return r.stdout
def main(name):
 if not re.fullmatch(r'td02_[0-9]{8}_[0-9]{2}',name):raise ValueError('Expected td02_YYYYMMDD_NN')
 work=ROOT/'target/team-discovery'/name;work.mkdir(parents=True,exist_ok=False)
 base=A/'target/team-discovery/td01_20261014_04';private=A/'docs/dev-ops/ab-v2/.local/td01_20261014_04'
 assert sha(base/'tested-app.jar')==load(ROOT/'docs/team-discovery-a-release.json')['aJarSha256']
 assert sha(Path('C:/Users/wanghao/.m2/repository/cn/bugstack/group-buy-market-contract/1.1.0-td.1/group-buy-market-contract-1.1.0-td.1.jar'))==load(ROOT/'docs/team-discovery-contract-lock.json')['sha256']
 spec=importlib.util.spec_from_file_location('fixture',ROOT/'docs/tests/prepare-td00-fixture.py');db=importlib.util.module_from_spec(spec);spec.loader.exec_module(db)
 schema='group_buy_market_td01_20261014_04_3';before=db.fingerprint(schema)
 original=load(ROOT/'docs/tests/td00-acceptance.json')['originalFinancialTables'];original_before={k:db.fingerprint(k,v) for k,v in original.items()}
 images=load(ROOT/'deploy/b06/images.lock.json');network='zj-'+name.replace('_','-');redis=network+'-redis';provider=network+'-a';owned=[]
 report={'stage':'TD-02','runName':name,'status':'RUNNING','aSchema':schema,'aBefore':before,'originalBefore':original_before,'checks':{}}
 def save():(work/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 save()
 try:
  cmd(DOCKER+['network','create','--label','td02.owner='+name,network])
  cmd(DOCKER+['run','-d','--name',redis,'--label','td02.owner='+name,'--network',network,'--network-alias','td01-redis','--memory','64m','--env-file',private/'redis.env',images['redis'],'sh','-c','exec redis-server --requirepass "$TD01_REDIS_PASSWORD" --save "" --appendonly no']);owned.append(redis)
  classes=work/'test-classes';classes.mkdir()
  cp=os.pathsep.join([str(classes),str(base/'test-classes'),str(base/'classes'),str(base/'lib/*')])
  cmd(['C:/Program Files/Java/jdk-21/bin/javac.exe','--release','8','-cp',cp,'-d',classes,ROOT/'docs/tests/td02/HoldAProvider.java'])
  cmd(DOCKER+['create','--name',provider,'--label','td02.owner='+name,'--memory','768m','--network','zj-market-b06_data','-p','50052:50052','--env-file',private/'live-tls.env','--mount','type=bind,src='+str(private)+',dst=/private,readonly','--mount','type=bind,src='+str(base)+',dst=/a,readonly','--mount','type=bind,src='+str(work)+',dst=/work','-w','/work','--entrypoint','java',images['java8'],'-XX:ActiveProcessorCount=2','-Xmx384m','-Dlogback.configurationFile=/private/logback.xml','-cp','/work/test-classes:/a/test-classes:/a/classes:/a/lib/*','cn.bugstack.test.v2.HoldAProvider']);owned.append(provider)
  cmd(DOCKER+['network','connect',network,provider]);cmd(DOCKER+['start',provider])
  for _ in range(90):
   logs=subprocess.run(DOCKER+['logs',provider],capture_output=True,text=True).stdout
   if 'TD02_PROVIDER_READY' in logs:break
   state=cmd(DOCKER+['inspect','--format','{{.State.Status}}',provider]).strip()
   if state!='running':raise RuntimeError('A provider stopped before ready')
   time.sleep(1)
  else:raise RuntimeError('A provider did not become ready')
  report['checks']['realAProviderReady']=True;save()
  env=os.environ.copy();values={}
  for line in (private/'live-tls.env').read_text().splitlines():
   if '=' in line:
    k,v=line.split('=',1);values[k]=v
  env.update({'TD02_A_URL':'tri://127.0.0.1:50052?ssl-enabled=true','TD02_RPC_SECRET':values['TD01_RPC_SECRET'],'TD02_TLS_CERT':str(private/'tls/certificate.pem'),'TD02_TLS_KEY':str(private/'tls/private-key.pem'),'TD02_STOP_FILE':str(work/'stop'),'TD02_METRICS':str(work/'http-metrics.json')})
  mvn="& .\\scripts\\mvn.ps1 -MavenArguments @('-B','-o','-pl','zj-market-app','-am','-Dtest=TeamDiscoveryBackendTest,TeamDiscoveryHttpTest,TeamDiscoveryGateTest','-Dsurefire.failIfNoSpecifiedTests=false','test')"
  result=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-Command',mvn],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
  text=(result.stdout or '')+'\n'+(result.stderr or '')
  for key in ['TD01_RPC_SECRET','TD01_DB_PASSWORD']:
   text=text.replace(values[key],'[REDACTED]')
  (work/'b-http-test.log').write_text(text,encoding='utf-8')
  if result.returncode:raise RuntimeError('B HTTP test failed; see ignored b-http-test.log')
  report['checks']['realBHttpToRealATls']=True
  report['httpTiming']=load(work/'http-metrics.json');report['checks']['httpP95Under1000Millis']=report['httpTiming']['httpP95Millis']<=1000
  report['aAfter']=db.fingerprint(schema);report['checks']['aBusinessRowsUnchanged']=report['aBefore']==report['aAfter']
  report['originalAfter']={k:db.fingerprint(k,v) for k,v in original.items()};report['checks']['originalBusinessRowsUnchanged']=report['originalBefore']==report['originalAfter']
  assert all(report['checks'].values());report['status']='PASSED';save()
 except Exception as e:
  report['status']='FAILED';report['error']=str(e);save();raise
 finally:
  (work/'stop').touch()
  for item in reversed(owned):
   check=subprocess.run(DOCKER+['inspect','--format','{{index .Config.Labels "td02.owner"}}',item],capture_output=True,text=True)
   if check.returncode==0 and check.stdout.strip()==name:subprocess.run(DOCKER+['rm','-f',item],capture_output=True)
  check=subprocess.run(DOCKER+['network','inspect','--format','{{index .Labels "td02.owner"}}',network],capture_output=True,text=True)
  if check.returncode==0 and check.stdout.strip()==name:subprocess.run(DOCKER+['network','rm',network],capture_output=True)
  if 'aAfter' not in report:
   report['aAfter']=db.fingerprint(schema);report['checks']['aBusinessRowsUnchanged']=report['aBefore']==report['aAfter']
   report['originalAfter']={k:db.fingerprint(k,v) for k,v in original.items()};report['checks']['originalBusinessRowsUnchanged']=report['originalBefore']==report['originalAfter'];save()
 print(json.dumps({'status':report['status'],'report':str(work/'report.json')}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);main(p.parse_args().run_name)
