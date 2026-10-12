"""Owned B065 fault runner. A durable inverse is saved BEFORE every runtime mutation.
No volume removal, schema changes, shared service operations, or host/daemon restarts.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,contextlib,hashlib,importlib.util,json,os,re,shutil,subprocess,time
import yaml
ROOT=Path(__file__).resolve().parents[1];PROJECT='zj-market-b06';HOME=ROOT/'.local/b06/faults';RUNTIME=ROOT/'.local/b06/runtime';CONTROL=ROOT/'.local/b06/control'
SERVICES=('mysql','redis','namesrv','broker','marketing-a','market-b','web')
def stamp():return datetime.now(timezone.utc).isoformat()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def atomic(path,data):
 t=path.with_suffix('.tmp');t.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');t.replace(path)
def require(value,code):
 if not value:raise RuntimeError(code)
@contextlib.contextmanager
def deployment_lock():
 with (CONTROL/'command.lock').open('a+b') as f:
  f.seek(0);f.write(b'0');f.flush();f.seek(0)
  if os.name=='nt':
   import msvcrt
   msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
  else:
   import fcntl
   fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  try:yield
  finally:
   if os.name=='nt':f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
   else:fcntl.flock(f.fileno(),fcntl.LOCK_UN)
class Faults:
 def __init__(self,batch,recover=False):
  require(bool(re.fullmatch(r'b065-[a-z0-9-]+',batch)),'INVALID_BATCH');self.batch=batch;self.work=HOME/batch
  if recover:require(self.work.exists(),'NO_RECOVERY_JOURNAL')
  else:require(not self.work.exists(),'FRESH_BATCH_REQUIRED');self.work.mkdir(parents=True)
  self.d=module('deployment',ROOT/'scripts/b06-deployment.py').Deployment('desktop-linux');self.obsmod=module('observer',ROOT/'scripts/b06-observability.py');self.o=self.obsmod.Observer()
  self.report=json.loads((self.work/'progress.json').read_text()) if recover else {'stage':'B-06.5','runName':batch,'status':'RUNNING','startedAt':stamp(),'checks':[],'timeline':[],'samples':[]}
  self.actions=json.loads((self.work/'recovery.json').read_text()) if recover else [];self.save()
 def save(self):atomic(self.work/'progress.json',self.report);atomic(self.work/'recovery.json',self.actions)
 def run(self,label,args,stdin=None,ok=True,timeout=180):
  r=subprocess.run([str(a) for a in args],input=stdin,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
  output=r.stdout+r.stderr
  for v in self.d.values.values():output=output.replace(str(v),'[REDACTED]')
  (self.work/(str(time.time_ns())+'-'+label+'.log')).write_text(output,encoding='utf-8')
  if ok:require(r.returncode==0,label+'_FAILED')
  return r
 def docker(self,label,args,**kw):return self.run(label,self.d.docker+args,**kw)
 def inspect(self,service):
  require(service in SERVICES,'SERVICE_NOT_ALLOWLISTED');v=json.loads(self.docker('identity-'+service,['inspect',PROJECT+'-'+service+'-1']).stdout)[0];labels=v['Config']['Labels']
  require(labels.get('com.docker.compose.project')==PROJECT and labels.get('com.docker.compose.service')==service,'OWNERSHIP_MISMATCH')
  return {'id':v['Id'],'image':v['Image'],'restart':v['HostConfig']['RestartPolicy'],'networks':v['NetworkSettings']['Networks'],'command':v['Config']['Cmd'],'extraHosts':v['HostConfig']['ExtraHosts'],'state':{k:v['State'].get(k) for k in ('Running','ExitCode','OOMKilled','Health','StartedAt','FinishedAt')}}
 def check(self,name,value,detail=None):
  require(value,name);self.report['checks'].append({'name':name,'at':stamp(),'status':'PASSED',**({'evidence':detail} if detail is not None else {})});self.save();print('PASS '+name,flush=True)
 def event(self,name,**detail):self.report['timeline'].append({'at':stamp(),'event':name,**detail});self.save();print('EVENT '+name,flush=True)
 def query(self,sql):return self.docker('query',['exec','-i',PROJECT+'-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --skip-column-names'],stdin=sql).stdout.strip()
 def jsonquery(self,sql):
  value=self.query(sql);return None if value=='NULL' else json.loads(value)
 def wait(self,name,fn,predicate,seconds=150):
  end=time.monotonic()+seconds;last=None
  while time.monotonic()<end:
   last=fn()
   if predicate(last):self.check(name,True,last);return last
   time.sleep(2)
  atomic(self.work/'last-wait.json',{'name':name,'value':last});raise RuntimeError(name+'_TIMEOUT')
 def healthy(self,service):return self.wait('healthy-'+service,lambda:self.inspect(service)['state'],lambda v:v['Running'] and v['Health']['Status']=='healthy',180)
 def client(self,action,*args):
  r=self.run('http-'+action,['node',ROOT/'docs/tests/b06-fault-client.mjs',action,self.batch,*args],timeout=180)
  return json.loads(r.stdout.strip().splitlines()[-1])
 def fixture(self):return json.loads((self.work/'fixture.json').read_text())
 def oid(self,name):return self.fixture()['orders'][name]['orderId']
 def order(self,name):
  oid=self.oid(name)
  return self.jsonquery(f"SELECT JSON_OBJECT('status',o.business_status,'reservation',r.state,'payments',(SELECT COUNT(*) FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id),'successful',(SELECT COUNT(*) FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id AND p.funds_state='SUCCEEDED'),'accepted',(SELECT COUNT(*) FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id AND p.a_acceptance='ACCEPTED'),'released',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='RELEASE'),'confirmed',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='CONFIRM'),'fulfillments',(SELECT COUNT(*) FROM zj_market_b06.b_fulfillment f WHERE f.order_id=o.order_id)) FROM zj_market_b06.b_market_order o JOIN zj_market_b06.b_inventory_reservation r ON r.order_id=o.order_id WHERE o.order_id='{oid}';")
 def closed(self,name):return self.wait('closed-once-'+name,lambda:self.order(name),lambda v:v['status']=='CLOSED' and v['reservation']=='RELEASED' and v['released']==1 and v['payments']==0)
 def sample(self,name):
  v=self.o.sample();atomic(self.work/(name+'-observation.json'),v)
  stats=self.docker('resources-'+name,['stats','--no-stream','--format','{{json .}}']+[PROJECT+'-'+s+'-1' for s in SERVICES]).stdout
  self.report['samples'].append({'at':stamp(),'name':name,'health':v['health'],'resources':[json.loads(x) for x in stats.splitlines() if x.strip()]});self.save();return v
 def remember(self,action):self.actions.append(action);self.save();self.event('inverse-saved',kind=action['kind'],service=action.get('service'))
 def restore(self,action):
  service=action['service'];require(action['kind'] in ('runtime','network','container'),'UNKNOWN_INVERSE');require(action['kind']!='runtime' or service=='market-b','RUNTIME_SERVICE_DENIED');require(action['kind']!='network' or (service=='market-b' and action['network']==PROJECT+'_rpc'),'NETWORK_NOT_ALLOWLISTED');v=self.inspect(service)
  if action['kind']=='runtime':
   require(v['image']==action['baseline']['image'],'RUNTIME_IMAGE_DRIFT');self.run('restore-scheduler',self.d.compose+['-f',CONTROL/'capabilities.yml','up','-d','--no-deps','--force-recreate','--wait','--wait-timeout','180',service],timeout=240)
   v=self.inspect(service);require(v['command']==action['baseline']['command'] and v['image']==action['baseline']['image'] and v['extraHosts']==action['baseline'].get('extraHosts'),'RUNTIME_RESTORE_DRIFT')
  else:
   require(v['id']==action['id'],'CONTAINER_REPLACED_REFUSE_RECOVERY')
   if action['kind']=='network':
    n=action['network'];network=self.docker('network-identity',['network','inspect',n]);nv=json.loads(network.stdout)[0];require(nv['Labels'].get('com.docker.compose.project')==PROJECT,'NETWORK_OWNERSHIP')
    if n not in v['networks']:
     args=['network','connect','--ip',action['endpoint']['IPAddress']]
     for alias in action['endpoint'].get('Aliases') or []:args+=['--alias',alias]
     self.docker('restore-network',args+[n,action['id']])
    endpoint=self.inspect(service)['networks'][n];require(endpoint['IPAddress']==action['endpoint']['IPAddress'] and set(endpoint.get('Aliases') or [])==set(action['endpoint'].get('Aliases') or []),'NETWORK_RESTORE_DRIFT')
   elif action['kind']=='container':
    policy=action['restart'];name=policy['Name'];name+=(':'+str(policy['MaximumRetryCount'])) if policy['Name']=='on-failure' and policy['MaximumRetryCount'] else ''
    self.docker('restore-restart',['update','--restart='+name,action['id']]);self.docker('restore-start',['start',action['id']]);require(self.inspect(service)['restart']==policy,'RESTART_RESTORE_DRIFT')
   else:raise RuntimeError('UNKNOWN_INVERSE')
  self.healthy(service);self.actions.remove(action);self.save();self.event('restored',service=service,kind=action['kind'])
 @contextlib.contextmanager
 def down(self,service,kill=False):
  v=self.inspect(service);require(v['state']['Running'],'REQUIRES_RUNNING_SERVICE');a={'kind':'container','service':service,'id':v['id'],'restart':v['restart'],'savedAt':stamp()};self.remember(a)
  try:
   self.docker('restart-disabled',['update','--restart=no',v['id']]);self.docker('interrupt-'+service,['kill','--signal','KILL',v['id']] if kill else ['stop','--time','10',v['id']]);state=self.inspect(service)['state'];self.check('actually-stopped-'+service,not state['Running'] and (not kill or state['ExitCode']==137),state);self.event('interrupted',service=service,mode='SIGKILL' if kill else 'stop');yield
  finally:self.restore(a)
 @contextlib.contextmanager
 def rpc_pin(self):
  baseline=self.inspect('market-b');endpoint=self.inspect('marketing-a')['networks'][PROJECT+'_rpc']['IPAddress'];overlay=self.work/'rpc-pin.yml'
  overlay.write_text(yaml.safe_dump({'services':{'market-b':{'extra_hosts':['marketing-a:'+endpoint]}}}))
  a={'kind':'runtime','service':'market-b','baseline':baseline,'savedAt':stamp()};self.remember(a)
  try:
   self.run('pin-rpc-endpoint',self.d.compose+['-f',CONTROL/'capabilities.yml','-f',overlay,'up','-d','--no-deps','--force-recreate','--wait','--wait-timeout','180','market-b'],timeout=240)
   actual=self.docker('verify-container-host-pin',['exec',PROJECT+'-market-b-1','getent','hosts','marketing-a']).stdout.split()[0];self.check('container-only-RPC-endpoint-pinned',actual==endpoint,{'endpoint':endpoint});yield
  finally:
   if a in self.actions:self.restore(a)
 @contextlib.contextmanager
 def network(self):
  service='market-b';n=PROJECT+'_rpc';v=self.inspect(service);require(n in v['networks'],'ENDPOINT_ABSENT');nv=json.loads(self.docker('network-owner',['network','inspect',n]).stdout)[0];require(nv['Labels'].get('com.docker.compose.project')==PROJECT,'NETWORK_OWNERSHIP')
  a={'kind':'network','service':service,'id':v['id'],'network':n,'endpoint':v['networks'][n],'savedAt':stamp()};self.remember(a)
  try:self.docker('disconnect-rpc',['network','disconnect',n,v['id']]);self.check('rpc-network-really-disconnected',n not in self.inspect(service)['networks']);self.event('interrupted',service=service,mode='rpc-network-disconnect');yield
  finally:self.restore(a)
 @contextlib.contextmanager
 def refund_pause(self):
  baseline=self.inspect('market-b');prop=self.work/'refund-pause.properties';prop.write_text('b.refund.scheduler-enabled=false\n');overlay=self.work/'refund-pause.yml'
  overlay.write_text(yaml.safe_dump({'services':{'market-b':{'volumes':[{'type':'bind','source':str(prop),'target':'/etc/b06/refund-fault.properties','read_only':True,'bind':{'create_host_path':False}}],'command':[baseline['command'][0]+',file:/etc/b06/refund-fault.properties']}}}))
  a={'kind':'runtime','service':'market-b','baseline':baseline,'savedAt':stamp()};self.remember(a)
  try:self.run('pause-refund-scheduler',self.d.compose+['-f',CONTROL/'capabilities.yml','-f',overlay,'up','-d','--no-deps','--force-recreate','--wait','--wait-timeout','180','market-b'],timeout=240);self.event('refund-scheduler-paused');yield a
  finally:
   if a in self.actions:self.restore(a)
 def tools(self):
  dest=self.work/'materials';dest.mkdir(exist_ok=True)
  for n in ['rpc-server-ca.pem','rpc-client.pem','rpc-client-key.pem','mq.pem','untrusted-ca.pem','untrusted.pem','untrusted-key.pem']:shutil.copyfile(RUNTIME/n,dest/n)
  (dest/'probe.properties').write_text(''.join(k+'='+self.d.values[k]+'\n' for k in ('mq_admin','mq_b','rpc')))
  (self.work/'bad-ca.properties').write_text('tls.test.mode.enable=false\ntls.client.authServer=true\ntls.client.trustCertPath=/run/secrets/untrusted-ca.pem\n')
  self.toolimages=json.loads((ROOT/'.local/b06/build/fault-tools/release.json').read_text())
 def transport(self,mode='stats',rpc=False,expect_fail=False):
  image=self.toolimages['transport']['id'];args=['run','--rm','--label','b06.fault-tool=true','--network',PROJECT+('_rpc' if rpc else '_mq'),'--memory','320m','--cpus','1','--pids-limit','128','--read-only','--tmpfs','/tmp:rw,nosuid,size=32m','--cap-drop','ALL','--security-opt','no-new-privileges:true']
  for source,dst in [(self.work/'materials','/test'),(self.work/'materials','/run/secrets'),(self.work/'bad-ca.properties' if mode=='bad-ca' else ROOT/'deploy/b06/config/mq-tls-client.properties','/etc/b06/mq-tls.properties')]:args+=['--mount',f'type=bind,src={source},dst={dst},readonly']
  if rpc:args += [image,'rpc',mode]
  else:args+=['--entrypoint','java',image,'-Xmx192m','-Duser.home=/tmp','-Dtls.enable=true','-Dtls.test.mode.enable=false','-Dtls.client.authServer=true','-Dtls.config.file=/etc/b06/mq-tls.properties','-cp','/tools/classes:/tools/libs/*','FaultTransportProbe',mode]
  r=self.docker('transport-'+mode,args,ok=not expect_fail,timeout=100)
  if expect_fail:self.check('fresh-client-route-unavailable',r.returncode!=0);return
  marker=('PROBE_REJECTED' if mode in ('no-client','bad-client') else 'PROBE_PASS') if rpc else ('FAULT_TRANSPORT_REJECTED' if mode in ('bad-secret','bad-ca','denied-topic') else 'FAULT_TRANSPORT_PASS')
  self.check(('rpc-' if rpc else 'mq-')+mode,marker in r.stdout)
 def refund_tool(self,action):
  args=['run','--rm','--label','b06.fault-tool=true','--network',PROJECT+'_data','--memory','320m','--cpus','1','--pids-limit','128','--read-only','--tmpfs','/tmp:rw,nosuid,size=32m','--cap-drop','ALL','--security-opt','no-new-privileges:true']
  for source,dst in [(RUNTIME/'b.properties','/run/secrets/b.properties'),(RUNTIME/'mysql-trust.p12','/run/secrets/mysql-trust.p12'),(self.work/'refunds.properties','/test/refunds.properties')]:args+=['--mount',f'type=bind,src={source},dst={dst},readonly']
  r=self.docker('refund-'+action,args+[self.toolimages['refund']['id'],action]);self.check('refund-'+action,'REFUND_FAULT_PASS' in r.stdout)
 def recover(self):
  errors=[]
  for action in list(reversed(self.actions)):
   try:self.restore(action)
   except Exception as e:errors.append(str(e))
  self.report['recoveryErrors']=errors;self.save();require(not errors,'RECOVERY_INCOMPLETE')
def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['run','recover','security']);p.add_argument('--run-name',required=True);a=p.parse_args();obsmod=module('observer_lock',ROOT/'scripts/b06-observability.py')
 with deployment_lock(),obsmod.exclusive():
  f=Faults(a.run_name,a.command=='recover')
  if a.command=='recover':f.recover();print('RECOVERY_COMPLETE');return
  try:
   f.d.capacity();f.d.ready();require(f.d.state()['mode']=='open' and f.d.state()['phase']=='READY','OPEN_READY_REQUIRED');f.tools()
   if a.command=='security':
    f.transport();f.transport('bad-secret');f.transport('denied-topic');f.transport('bad-ca');f.transport();f.transport('signed',True);f.transport('bad-hmac',True);f.transport('no-client',True);f.transport('bad-client',True);f.transport('signed',True)
   else:module('fault_matrix',ROOT/'docs/tests/run-b06-faults.py').run(f)
   f.report['status']='PASSED';f.report['finishedAt']=stamp();f.save()
  except BaseException as e:
   f.report['status']='FAILED';f.report['error']=type(e).__name__+': '+str(e);f.save();raise
  finally:f.recover()
 print('B065 '+f.report['status'],flush=True)
if __name__=='__main__':main()
