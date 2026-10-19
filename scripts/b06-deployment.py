"""Explicit, owned Windows Docker deployment. Never targets shared containers or databases."""
from pathlib import Path
import argparse,subprocess,json,hashlib,secrets,os,re,time,shutil
import yaml
ROOT=Path(__file__).resolve().parents[1]
PROJECT='zj-market-ux'
CONTROL=ROOT/'.local/b06/control'
RUNTIME=ROOT/'.local/b06/runtime'
BUILD=ROOT/'.local/b06/build'
GIB=1024**3

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inputs():
 paths=list((ROOT/'deploy/b06/init').glob('*'))+list((ROOT/'zj-market-infrastructure/src/main/resources/db/migration').glob('*.sql'))
 return {str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in sorted(paths) if p.is_file() and p.suffix!=".java"}

class Deployment:
 def __init__(self,context):
  self.docker=['docker','--context',context];self.counter=0
  self.values=json.loads((RUNTIME/'private/values.json').read_text())
  self.logs=CONTROL/'logs';self.logs.mkdir(parents=True,exist_ok=True)
  self.compose=self.docker+['compose','-p',PROJECT,'--env-file',str(BUILD/'release.env'),'-f',str(ROOT/'deploy/b06/compose.yml')]
 def run(self,label,args,stdin=None,expected=None,timeout=240):
  self.counter+=1;r=subprocess.run([str(a) for a in args],input=stdin,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
  text=r.stdout+r.stderr
  for value in self.values.values():text=text.replace(str(value),'[REDACTED]')
  if (CONTROL/'deployment.properties').exists():
   for line in (CONTROL/'deployment.properties').read_text().splitlines():
    if '.password=' in line:text=text.replace(line.split('=',1)[1],'[REDACTED]')
  stamp=time.time_ns();(self.logs/(str(stamp)+'-'+label+'.log')).write_text(text,encoding='utf-8')
  if r.returncode or expected and expected not in r.stdout:raise RuntimeError(label+' failed; see private control/logs')
  print('PASS '+label,flush=True);return r.stdout
 def admin(self,label,sql):
  return self.run(label,self.docker+['exec','-i',PROJECT+'-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --skip-column-names'],sql)
 def save(self,state):
  path=CONTROL/'state.json';tmp=CONTROL/'state.tmp';tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(path)
 def state(self):
  s=json.loads((CONTROL/'state.json').read_text());
  if s['project']!=PROJECT:raise RuntimeError('Wrong deployment ownership record')
  if s['inputs']!=inputs():raise RuntimeError('Initialization inputs changed; require a separately reviewed migration/release')
  return s
 def ownership(self):
  rows=json.loads(self.run('mysql-identity',self.docker+['inspect',PROJECT+'-mysql-1']))
  labels=rows[0]['Config']['Labels']
  if labels.get('com.docker.compose.project')!=PROJECT or labels.get('com.docker.compose.service')!='mysql':raise RuntimeError('Wrong container ownership')
 def tool(self,mode):
  state=self.state()
  image=json.loads((ROOT/'deploy/b06/images.lock.json').read_text())['redis']
  mem=self.run('maintenance-tool-memory-check',self.docker+['run','--rm','--network','none','--memory','32m','--entrypoint','cat',image,'/proc/meminfo'])
  if int(re.search(r'MemAvailable:\s+(\d+)',mem).group(1))*1024 < (448 if mode in ['verify','a-init'] else 768)*1024**2:raise RuntimeError('Insufficient live memory for maintenance tool and reserve')
  args=self.docker+['run','--rm','--network',PROJECT+'_data','--memory',('192m' if mode in ['verify','a-init'] else '512m'),'--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,nosuid,size=64m','--mount','type=bind,src='+str(ROOT/'deploy/b06/init')+',dst=/input,readonly','--mount','type=bind,src='+str(CONTROL)+',dst=/output']
  for name in ['deployment.properties']:
   args+=['--mount','type=bind,src='+str(CONTROL/name)+',dst=/run/secrets/'+name+',readonly']
  for name in ['b.properties','mysql-trust.p12','identity-key.pem','identity-public.pem']:
   args+=['--mount','type=bind,src='+str(RUNTIME/name)+',dst=/run/secrets/'+name+',readonly']
  # Public B config includes new event scope; no broker/RPC used by seed bootstrap.
  args+=['--mount','type=bind,src='+str(ROOT/'deploy/b06/config/b.properties')+',dst=/config/b.properties,readonly',state['maintenanceImage'],mode]
  return self.run('tool-'+mode,args,expected='DEPLOYMENT_PASS '+mode)
 def fingerprint(self):
  # DDL only; excludes row counts/AUTO_INCREMENT counters and data/timestamps.
  sql="SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,ORDINAL_POSITION,COLUMN_TYPE,IS_NULLABLE,COALESCE(COLUMN_DEFAULT,'<NULL>'),EXTRA,COALESCE(COLLATION_NAME,'') FROM information_schema.COLUMNS WHERE TABLE_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION; SELECT TABLE_SCHEMA,TABLE_NAME,INDEX_NAME,NON_UNIQUE,SEQ_IN_INDEX,COLUMN_NAME,COALESCE(SUB_PART,0) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY TABLE_SCHEMA,TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX; SELECT TABLE_SCHEMA,TABLE_NAME,ENGINE,TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY TABLE_SCHEMA,TABLE_NAME; SELECT CONSTRAINT_SCHEMA,TABLE_NAME,CONSTRAINT_NAME,CONSTRAINT_TYPE,ENFORCED FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY CONSTRAINT_SCHEMA,TABLE_NAME,CONSTRAINT_NAME; SELECT CONSTRAINT_SCHEMA,TABLE_NAME,CONSTRAINT_NAME,COLUMN_NAME,ORDINAL_POSITION,COALESCE(REFERENCED_TABLE_SCHEMA,''),COALESCE(REFERENCED_TABLE_NAME,''),COALESCE(REFERENCED_COLUMN_NAME,'') FROM information_schema.KEY_COLUMN_USAGE WHERE CONSTRAINT_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY CONSTRAINT_SCHEMA,TABLE_NAME,CONSTRAINT_NAME,ORDINAL_POSITION; SELECT CONSTRAINT_SCHEMA,CONSTRAINT_NAME,CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY CONSTRAINT_SCHEMA,CONSTRAINT_NAME; SELECT CONSTRAINT_SCHEMA,TABLE_NAME,CONSTRAINT_NAME,UPDATE_RULE,DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_SCHEMA IN ('group_buy_market_b06','zj_market_b06') ORDER BY CONSTRAINT_SCHEMA,TABLE_NAME,CONSTRAINT_NAME;"
  return hashlib.sha256(self.admin('schema-fingerprint',sql).encode()).hexdigest()
 def history(self):
  return hashlib.sha256(self.admin('migration-history',"SELECT version,script,checksum,success FROM zj_market_b06.flyway_schema_history ORDER BY installed_rank;").encode()).hexdigest()
 def ready(self):
  self.ownership();s=self.state()
  if not s['initialized']:raise RuntimeError('Explicit initialization not completed')
  if self.history()!=s['migrationHistoryHash']:raise RuntimeError('Migration history drift: refusing startup/admission')
  if self.fingerprint()!=s['schemaFingerprint']:raise RuntimeError('Schema drift: refusing business startup/admission')
  self.tool('verify')
  result=self.admin('migrators-locked',"SELECT User,account_locked,ssl_type FROM mysql.user WHERE User IN ('a_migrator','b_migrator') ORDER BY User;")
  if result.count('Y\tANY')!=2:raise RuntimeError('Migrators must be locked and require SSL')
  return s
 def capacity(self):
  image=json.loads((ROOT/'deploy/b06/images.lock.json').read_text())['redis']
  info=self.run('docker-available-memory',self.docker+['run','--rm','--network','none','--entrypoint','cat',image,'/proc/meminfo'])
  available=int(re.search(r'MemAvailable:\s+(\d+)',info).group(1))*1024
  evidence={'linuxAvailableBytes':available,'persistentLimitsBytes':int(3*GIB),'reserveBytes':int(.25*GIB)}
  if os.name=='nt':
   value=subprocess.check_output(['powershell','-NoProfile','-Command','(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory'],text=True);evidence['windowsAvailableBytes']=int(value.strip())*1024
   disks=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DeviceID -in @('C:','D:') } | Select-Object DeviceID,FreeSpace | ConvertTo-Json -Compress"],text=True))
   evidence['hostDiskFreeBytes']={x['DeviceID']:x['FreeSpace'] for x in disks}
   if evidence['hostDiskFreeBytes'].get('C:',0)<20*GIB or evidence['hostDiskFreeBytes'].get('D:',0)<80*GIB:raise RuntimeError('Host C/D disk space below deployment thresholds')
   if evidence['windowsAvailableBytes']<1.5*GIB:raise RuntimeError('Host available memory below 1.5GiB')
  owned=self.run('owned-memory',self.docker+['stats','--no-stream','--format','{{.MemUsage}}']+self.run('owned-running-names',self.docker+['ps','--filter','label=com.docker.compose.project='+PROJECT,'--format','{{.Names}}']).splitlines()) if self.run('owned-running',self.docker+['ps','--filter','label=com.docker.compose.project='+PROJECT,'--format','{{.ID}}']).strip() else ''
  used=0
  for row in owned.splitlines():
   m=re.match(r'([0-9.]+)([KMGT]?i?B)',row.split('/')[0].strip())
   if m:used+=float(m[1])*{'B':1,'KiB':1024,'MiB':1024**2,'GiB':1024**3,'kB':1000,'MB':1000**2,'GB':1000**3}[m[2]]
  evidence['ownedRunningBytes']=int(used)
  if available+used<3.25*GIB:raise RuntimeError('Docker memory available plus owned usage below full-stack limits plus reserve (3.25GiB)')
  (CONTROL/'capacity.json').write_text(json.dumps(evidence,indent=2)+'\n')
 def initialize(self):
  provenance=json.loads((ROOT/'deploy/b06/init/a-schema-provenance.json').read_text())
  if digest(ROOT/'deploy/b06/init/a-empty-schema.sql')!=provenance['outputSha256']:raise RuntimeError('A schema provenance mismatch')
  state_file=CONTROL/'state.json'
  if not state_file.exists():
   volumes=self.run('existing-volumes',self.docker+['volume','ls','--filter','label=com.docker.compose.project='+PROJECT,'--format','{{.Name}}']).strip()
   containers=self.run('existing-containers',self.docker+['ps','-a','--filter','label=com.docker.compose.project='+PROJECT,'--format','{{.ID}}']).strip()
   if volumes or containers:raise RuntimeError('Unowned deployment exists; refusing adoption')
   self.capacity()
   image=json.loads(self.run('maintenance-image',self.docker+['image','inspect','zj-market-b06/maintenance:b062']))[0]['Id']
   state={'project':PROJECT,'inputs':inputs(),'initialized':False,'mode':'maintenance','maintenanceImage':image,'sdkImage':json.loads(self.run('sdk-image',self.docker+['image','inspect','zj-market-b06/security-tools:b061']))[0]['Id'],'schemaFingerprint':None}
   generated={n:secrets.token_hex(32) for n in ['a_migrator','b_migrator','b06operator','b06buyer','b06buyer2']}
   urls={}
   for who,schema in [('a_runtime','group_buy_market_b06'),('b_runtime','zj_market_b06'),('a_migrator','group_buy_market_b06'),('b_migrator','zj_market_b06')]:
    urls[who+'.url']='jdbc:mysql://mysql:3306/'+schema+'?serverTimezone=UTC&sslMode=VERIFY_IDENTITY&trustCertificateKeyStoreUrl=file:/run/secrets/mysql-trust.p12&trustCertificateKeyStoreType=PKCS12&trustCertificateKeyStorePassword='+self.values['truststore']
    urls[who+'.user']=who;urls[who+'.password']=self.values['a_db' if who=='a_runtime' else 'b_db'] if who.endswith('runtime') else generated[who]
   for who in ['b06operator','b06buyer','b06buyer2']:urls[who+'.password']=generated[who]
   (CONTROL/'deployment.properties').write_text(''.join(k+'='+v+'\n' for k,v in urls.items()))
   (CONTROL/'demo-accounts.json').write_text(json.dumps({u:{'loginName':u,'password':generated[u]} for u in ['b06operator','b06buyer','b06buyer2']},indent=2)+'\n')
   self.save(state)
   # Reuse material ACL protection; no existing secrets are regenerated.
   import importlib.util
   spec=importlib.util.spec_from_file_location('materials',ROOT/'scripts/prepare-b06-secrets.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.protect_windows(CONTROL)
  state=self.state()
  self.run('middleware-up',self.compose+['up','-d','--wait','--wait-timeout','180','mysql','redis','namesrv','broker'])
  self.ownership()
  if state['initialized']:
   self.ready();self.mq();print('Already initialized; validated without reseeding',flush=True);return
  # This state record precedes creation; only dedicated schemas/principals are touched.
  props=dict(line.split('=',1) for line in (CONTROL/'deployment.properties').read_text().splitlines())
  sql=''
  for schema in ['group_buy_market_b06','zj_market_b06']:sql+='CREATE DATABASE IF NOT EXISTS '+schema+' CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;\n'
  for who in ['a_runtime','b_runtime','a_migrator','b_migrator']:
   sql+="CREATE USER IF NOT EXISTS '"+who+"'@'%' IDENTIFIED BY '"+props[who+'.password']+"' REQUIRE SSL;\n"
  for who,schema in [('a_migrator','group_buy_market_b06'),('b_migrator','zj_market_b06')]:sql+="GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,DROP,INDEX,REFERENCES ON "+schema+".* TO '"+who+"'@'%'; ALTER USER '"+who+"'@'%' ACCOUNT UNLOCK;\n"
  self.admin('schemas-and-principals',sql)
  try:
   self.tool('a-init');self.tool('migrate')
   for who,schema in [('a_runtime','group_buy_market_b06'),('b_runtime','zj_market_b06')]:
    tables=(ROOT/'deploy/b06/init'/f'{who}-tables.txt').read_text().splitlines()
    self.admin('grant-'+who,''.join('GRANT SELECT,INSERT,UPDATE,DELETE ON '+schema+'.'+t+" TO '"+who+"'@'%';\n" for t in tables))
   self.tool('verify');self.tool('seed')
   goods=(CONTROL/'seed-goods-id.txt').read_text().strip()
   if not re.fullmatch('[a-f0-9-]{36}',goods):raise RuntimeError('Unexpected seed product identity')
   self.seed_a(goods)
  finally:self.admin('lock-migrators',"ALTER USER 'a_migrator'@'%' ACCOUNT LOCK; ALTER USER 'b_migrator'@'%' ACCOUNT LOCK;")
  self.mq();state['schemaFingerprint']=self.fingerprint();state['migrationHistoryHash']=self.history();state['initialized']=True;self.save(state);self.ready()
 def seed_a(self,goods):
  # Fixed activity definition. Repeated run preserves original deadlines, never rewrites orders/funds.
  sql="USE group_buy_market_b06; START TRANSACTION; INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) SELECT '60000101','B06 demo discount','Ten yuan reduction',0,'ZJ','10' WHERE NOT EXISTS(SELECT 1 FROM group_buy_discount WHERE discount_id='60000101'); INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time) SELECT 600001,'B06 demo activity','60000101',1,10,2,15,1,UTC_TIMESTAMP()-INTERVAL 1 HOUR,UTC_TIMESTAMP()+INTERVAL 30 DAY WHERE NOT EXISTS(SELECT 1 FROM group_buy_activity WHERE activity_id=600001); INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) SELECT 'b06','web',600001,'"+goods+"' WHERE NOT EXISTS(SELECT 1 FROM sc_sku_activity WHERE source='b06' AND channel='web' AND goods_id='"+goods+"'); COMMIT;"
  self.admin('seed-a-activity',sql)
 def mq(self):
  test=CONTROL/'mq';test.mkdir(exist_ok=True)
  (test/'probe.properties').write_text(''.join(k+'='+self.values[k]+'\n' for k in ['mq_admin','mq_a','mq_b','rpc']))
  shutil.copyfile(RUNTIME/'mq.pem',test/'mq.pem')
  self.run('mq-topics-groups',self.docker+['run','--rm','--network',PROJECT+'_mq','--memory','320m','--mount','type=bind,src='+str(test)+',dst=/test,readonly','--mount','type=bind,src='+str(test)+',dst=/run/secrets,readonly','--mount','type=bind,src='+str(ROOT/'deploy/b06/config/mq-tls-client.properties')+',dst=/etc/b06/mq-tls.properties,readonly',self.state()['sdkImage'],'mq','deploy-init'],expected='PROBE_PASS')
 def configuration(self,mode):
  flags={k:True for k in ['product','inventory','order','trade','trial','sync','payment']}
  text=''.join('b.'+k+'.enabled=true\n' for k in flags)+'b.trade.events-enabled=true\n'
  for k in ['b.payment.checkout-enabled','b.reconciliation.enabled','b.refund.enabled','b.team-discovery.enabled']:text+=k+'='+str(mode=='open').lower()+'\n'
  text+='b.reconciliation.recovery-enabled=true\nb.refund.recovery-enabled=true\n'
  (CONTROL/'capabilities.properties').write_text(text)
  overlay={'services':{'market-b':{'volumes':[{'type':'bind','source':str(CONTROL/'capabilities.properties'),'target':'/etc/b06/capabilities.properties','read_only':True,'bind':{'create_host_path':False}}],'command':['--spring.config.additional-location=file:/etc/b06/application.properties,file:/run/secrets/b.properties,file:/etc/b06/capabilities.properties']}}}
  (CONTROL/'capabilities.yml').write_text(yaml.safe_dump(overlay,sort_keys=False))
 def gateway(self,mode):
  env=os.environ.copy();env['B06_ADMISSION_FILE']=str(ROOT/'deploy/b06/config'/('admission-'+mode+'.conf'))
  # Environment is local to this subprocess. Recreate avoids stale bind inode / implicit live mutation.
  args=self.compose+['-f',str(CONTROL/'capabilities.yml'),'up','-d','--no-deps','--force-recreate','--wait','--wait-timeout','90','web']
  r=subprocess.run(args,env=env,capture_output=True,text=True);(self.logs/(str(time.time_ns())+'-gateway-'+mode+'.log')).write_text(r.stdout+r.stderr)
  if r.returncode:
   subprocess.run(self.docker+['stop',PROJECT+'-web-1'],capture_output=True,text=True)
   raise RuntimeError('Gateway mode change failed; owned public gateway stopped to keep admission closed')
 def gateway_mode(self):
  value=self.run('actual-gateway-mode',['node',ROOT/'scripts/ux00-gateway-mode.mjs',RUNTIME/'web-ca.pem']).strip()
  if value not in ('NORMAL','MAINTENANCE'):raise RuntimeError('Unexpected public gateway mode')
  return 'open' if value=='NORMAL' else 'maintenance'
 def web_image_matches_release(self):
  settings=dict(line.split('=',1) for line in (BUILD/'release.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
  tag=settings.get('B06_WEB_IMAGE')
  if not tag:raise RuntimeError('Missing fixed UX Web image')
  expected=self.run('desired-web-image',self.docker+['image','inspect',tag,'--format','{{.Id}}']).strip()
  running=self.run('running-web-image',self.docker+['inspect',PROJECT+'-web-1','--format','{{.Image}}']).strip()
  return expected==running
 def preflight_start(self,state,mode,action):
  phase=state.get('phase')
  if phase not in ('READY','STOPPED','FAILED_GATE_CLOSED'):
   raise RuntimeError('Unsupported UX lifecycle phase; inspect status before changing the gate')
  if action=='start' and phase=='READY':
   raise RuntimeError('UX is already running; use ready/status or explicit maintenance')
  if phase=='READY' and state.get('mode')==mode and self.web_image_matches_release():
   self.ready()
   if self.gateway_mode()!=mode:raise RuntimeError('Actual UX gate differs from saved state')
   print('Already '+mode+'; validated without deployment',flush=True)
   return True
  return False
 def start(self,mode,action):
  state=self.state()
  # Reject unsupported or duplicate actions before changing files, containers or gate.
  if self.preflight_start(state,mode,action):return
  # Capacity is a precondition: rejection must leave an already-open UX gate intact.
  self.capacity()
  self.configuration('maintenance')
  state.update(mode='maintenance',phase='GATED',targetMode=mode);self.save(state)
  changed=False;open_gate=False
  try:
   if self.run('web-present',self.docker+['ps','--filter','name=^/'+PROJECT+'-web-1$','--format','{{.ID}}']).strip():self.gateway('maintenance')
   self.run('middleware-up',self.compose+['up','-d','--wait','--wait-timeout','180','mysql','redis','namesrv','broker'])
   self.ready();self.configuration(mode);changed=True
   self.run('a-ready-'+mode,self.compose+['-f',str(CONTROL/'capabilities.yml'),'up','-d','--wait','--wait-timeout','180','marketing-a'])
   self.run('b-reload-'+mode,self.compose+['-f',str(CONTROL/'capabilities.yml'),'up','-d','--no-deps','--force-recreate','--wait','--wait-timeout','180','market-b'])
   self.ready();self.gateway('maintenance')
   self.run('actual-sync-rpc-identity-ready',['node',ROOT/'docs/tests/b06-startup-client.mjs','ready',CONTROL,RUNTIME],expected='CLIENT_PASS')
   if mode=='open':
    self.gateway('open');open_gate=True
   if self.gateway_mode()!=mode:raise RuntimeError('Actual UX gate did not reach requested mode')
   state.update(mode=mode,phase='READY');self.save(state)
   self.run('container-resources',self.docker+['stats','--no-stream','--format','{{json .}}',PROJECT+'-mysql-1',PROJECT+'-redis-1',PROJECT+'-namesrv-1',PROJECT+'-broker-1',PROJECT+'-marketing-a-1',PROJECT+'-market-b-1',PROJECT+'-web-1'])
  except Exception:
   if open_gate:
    try:self.gateway('maintenance')
    except Exception:pass # gateway() stops the owned web on a failed mode change.
   self.configuration('maintenance');state.update(mode='maintenance',phase='FAILED_GATE_CLOSED');self.save(state)
   if changed:
    try:self.run('rollback-b-to-maintenance',self.compose+['-f',str(CONTROL/'capabilities.yml'),'up','-d','--no-deps','--force-recreate','--wait','--wait-timeout','120','market-b'])
    except Exception:pass # Original failure is retained; FAILED_GATE_CLOSED never claims full readiness.
   raise
 def stop(self):
  s=self.state();self.configuration('maintenance');self.gateway('maintenance');s.update(mode='maintenance',phase='STOPPING');self.save(s)
  self.run('owned-stack-stop',self.compose+['-f',str(CONTROL/'capabilities.yml'),'stop'])
  s['phase']='STOPPED';self.save(s)

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['init','start','open','maintenance','ready','status','stop']);p.add_argument('--context',default='desktop-linux');a=p.parse_args();d=Deployment(a.context)
 if a.action=='init':d.initialize()
 elif a.action in ['start','maintenance','open']:d.start('open' if a.action=='open' else 'maintenance',a.action)
 elif a.action=='ready':
  state=d.ready()
  if state.get('phase')!='READY':raise RuntimeError('UX dependencies are ready but public gate is not in READY phase')
  if d.gateway_mode()!=state.get('mode'):raise RuntimeError('Actual UX gate differs from saved state')
  print('UX_GATE_'+state['mode'].upper(),flush=True)
 elif a.action=='stop':d.stop()
 else:
  state=d.state();print('Gate mode: '+state['mode']+'; phase: '+state.get('phase','INITIALIZED'))
  if state.get('phase')=='READY':print('Actual gate: '+d.gateway_mode(),flush=True)
  d.run('status',d.compose+['ps'])
if __name__=='__main__':
 CONTROL.mkdir(parents=True,exist_ok=True)
 with (CONTROL/'command.lock').open('a+b') as lock:
  lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
  if os.name=='nt':
   import msvcrt
   msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  else:
   import fcntl
   fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  main()
