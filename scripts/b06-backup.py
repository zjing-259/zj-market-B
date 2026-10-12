"""B066 cold backup, isolated empty-volume restore and compatible packaging rollback.
No volume deletion, schema downgrade, shared project mutation or ordinary fault API.
"""
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,os,re,shutil,subprocess,time,tarfile
ROOT=Path(__file__).resolve().parents[1];HOME=ROOT/'.local/b06/backups';PROJECT='zj-market-b06'
SERVICES=('mysql','redis','namesrv','broker','marketing-a','market-b','web')
VOLUMES=('mysql-data','redis-data','broker-store','broker-logs','namesrv-logs')
HELPER=json.loads((ROOT/'deploy/b06/images.lock.json').read_text())['redis']
FINANCIAL="""SELECT order_id,payment_id,amount,funds_state,a_acceptance,success_hash,paid_at_ms FROM zj_market_b06.b_payment ORDER BY order_id;
SELECT order_id,refund_id,amount,funds_status,sync_status,release_status,success_hash FROM zj_market_b06.b_refund ORDER BY order_id,refund_id;
SELECT goods_id,available,reserved,sold FROM zj_market_b06.b_inventory_account ORDER BY goods_id;
SELECT order_id,kind,goods_id,delta_available FROM zj_market_b06.b_inventory_ledger ORDER BY order_id,kind;
SELECT order_id,state FROM zj_market_b06.b_inventory_reservation ORDER BY order_id;
SELECT order_id,status FROM zj_market_b06.b_fulfillment ORDER BY order_id;
SELECT team_id,reserved_count,paid_count FROM group_buy_market_b06.ab_team ORDER BY team_id;
SELECT consumer,producer,event_id,body_hash,processing_status,outcome FROM group_buy_market_b06.ab_inbox ORDER BY consumer,producer,event_id;"""
CHANNELS="""SELECT payment_id,gate,amount,currency,success_attempt_id,snapshot_hash,close_request_hash,close_result_hash FROM zj_market_b06.b_sim_payment ORDER BY payment_id;
SELECT attempt_id,payment_id,attempt_no,channel_transaction_id,state,request_hash,paid_at_ms FROM zj_market_b06.b_sim_attempt ORDER BY attempt_id;
SELECT refund_id,payment_id,amount,currency,root_hash,refunded_amount,success_attempt_id FROM zj_market_b06.b_sim_refund ORDER BY refund_id;
SELECT attempt_id,refund_id,attempt_no,request_hash,state,fact_hash FROM zj_market_b06.b_sim_refund_attempt ORDER BY attempt_id;"""
def stamp():return datetime.now(timezone.utc).isoformat()
def require(ok,message):
 if not ok:raise RuntimeError(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def atomic(path,data):
 path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
def valid_name(name):require(bool(re.fullmatch(r'b066-[a-z0-9-]{1,40}',name)),'INVALID_BATCH')
def validate_manifest(work):
 work=Path(work).resolve();marker=work/'COMPLETE.json';require(marker.is_file(),'INCOMPLETE_BACKUP');complete=json.loads(marker.read_text(encoding='utf-8'));require(sha(work/'manifest.json')==complete['manifestSha256'],'MANIFEST_HASH_MISMATCH');m=json.loads((work/'manifest.json').read_text(encoding='utf-8'));require(m.get('format')==2 and m['project']==PROJECT and set(m['volumes'])==set(VOLUMES),'BACKUP_SCOPE_MISMATCH')
 for name,h in m['files'].items():
  p=(work/name).resolve();require(p.is_relative_to(work) and p.is_file(),'UNSAFE_OR_MISSING_ARCHIVE');require(sha(p)==h,'BACKUP_HASH_MISMATCH')
 required={'images.tar','business-before.sql','original-event.json','compose-snapshot.json','state-before.json','recovery-tools.json','bundle/control/state.json','bundle/control/demo-accounts.json','bundle/runtime/private/values.json','bundle/images.lock.json'}|{n+'.tar' for n in VOLUMES}
 require(required<=set(m['files']),'MISSING_BACKUP_COMPONENT')
 with tarfile.open(work/'images.tar') as archive:
  exported=json.load(archive.extractfile('manifest.json'));config_ids={'sha256:'+hashlib.sha256(archive.extractfile(item['Config']).read()).hexdigest() for item in exported}
 require(set(m['images'])<=config_ids,'ARCHIVED_IMAGE_SET_INCOMPLETE')
 state=json.loads((work/'state-before.json').read_text(encoding='utf-8'))
 require(bool(state.get('inputs')),'MISSING_INITIALIZATION_INPUTS')
 for path,h in state['inputs'].items():
  name='bundle/init/'+Path(path).name if path.startswith('deploy/b06/init/') else 'bundle/migrations/'+Path(path).name if path.startswith('zj-market-infrastructure/src/main/resources/db/migration/') else None
  require(name is not None and name in m['files'] and sha(work/name)==h,'INITIALIZATION_INPUT_MISMATCH')
 for volume in VOLUMES:
  with tarfile.open(work/(volume+'.tar')) as archive:
   for member in archive:
    path=PurePosixPath(member.name);require(not path.is_absolute() and '..' not in path.parts,'UNSAFE_ARCHIVE_MEMBER')
    if member.issym() or member.islnk():
     target=PurePosixPath(member.linkname);allowed=volume=='mysql-data' and member.name in ['./mysql.sock','mysql.sock'] and member.linkname=='/var/run/mysqld/mysqld.sock'
     require(allowed or not target.is_absolute() and '..' not in target.parts,'UNSAFE_ARCHIVE_LINK')
 return m
def isolated_networks(config,project):
 require(set(config['networks'])=={'edge','rpc','data','redis','mq'},'RESTORE_NETWORK_SET')
 for name,v in config['networks'].items():
  require(not v.get('external',False),'EXTERNAL_RESTORE_NETWORK');v['name']=project+'_'+name
 return config
def compatible(release,state,jar):
 require(release.get('protocol')=='V18-opaque-rosterVersion','INCOMPATIBLE_PROTOCOL');require(release.get('schemaFingerprint')==state['schemaFingerprint'] and release.get('migrationHistoryHash')==state['migrationHistoryHash'],'INCOMPATIBLE_SCHEMA');require(release.get('businessJarSha256')==jar,'UNVERIFIED_BUSINESS_JAR');require(release['candidate']['id']!=release['rollbackImage'],'NOT_A_DISTINCT_RELEASE')
class Recovery:
 def __init__(self,name,existing=False):
  valid_name(name);self.name=name;self.work=HOME/name;self.clone='zj-market-'+name
  if existing:require(self.work.exists(),'MISSING_BATCH')
  else:
   require(not self.work.exists(),'FRESH_BATCH_REQUIRED');self.work.mkdir(parents=True);module('protect',ROOT/'scripts/prepare-b06-secrets.py').protect_windows(self.work)
  self.d=module('deployment_original',ROOT/'scripts/b06-deployment.py').Deployment('desktop-linux');self.docker=self.d.docker;self.report=json.loads((self.work/'progress.json').read_text(encoding='utf-8')) if existing else {'stage':'B-06.6','runName':name,'status':'RUNNING','startedAt':stamp(),'checks':[],'timeline':[],'scope':'Windows Docker cold-backup restore drill; no original volume replacement'}
  self.journal=json.loads((self.work/'recovery.json').read_text()) if existing else {}
  if not existing:self.report['sourceSha256']={f:sha(ROOT/f) for f in ['scripts/b06-backup.py','scripts/build-b06-recovery-tools.py','deploy/b06/verification/RecoveryReplayProbe.java','docs/tests/test-b06-backup.py','docs/tests/b06-recovery-gate.mjs']}
  self.save()
 def save(self):atomic(self.work/'progress.json',self.report);atomic(self.work/'recovery.json',self.journal)
 def event(self,name,**facts):self.report['timeline'].append({'at':stamp(),'event':name,**facts});self.save();print('EVENT '+name,flush=True)
 def check(self,name,ok,**facts):require(ok,name);self.report['checks'].append({'name':name,'status':'PASSED','at':stamp(),**facts});self.save();print('PASS '+name,flush=True)
 def run(self,label,args,stdin=None,timeout=240,sensitive=False,ok=True):
  t=time.monotonic();r=subprocess.run([str(x) for x in args],input=stdin,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
  text=r.stdout+r.stderr
  for v in self.d.values.values():text=text.replace(str(v),'[REDACTED]')
  log={'at':stamp(),'label':label,'exitCode':r.returncode,'seconds':round(time.monotonic()-t,3)}
  if not sensitive:log['output']=text
  atomic(self.work/(str(time.time_ns())+'-'+label+'.json'),log)
  if ok:require(r.returncode==0,label+'_FAILED')
  return r
 def docker_run(self,label,args,**kwargs):return self.run(label,self.docker+args,**kwargs)
 def inspect(self,project,service):
  require(project in [PROJECT,self.clone] and service in SERVICES,'UNOWNED_TARGET');v=json.loads(self.docker_run('inspect-'+service,['inspect',project+'-'+service+'-1']).stdout)[0];labels=v['Config']['Labels'];require(labels.get('com.docker.compose.project')==project and labels.get('com.docker.compose.service')==service,'OWNERSHIP_MISMATCH');return v
 def sql(self,project,query):
  require(project in [PROJECT,self.clone],'UNOWNED_SQL');return self.docker_run('sql-'+project,['exec','-i',project+'-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names'],stdin=query,sensitive=True).stdout
 def dump(self,project):
  return self.docker_run('business-dump-'+project,['exec',project+'-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysqldump -uroot --databases group_buy_market_b06 zj_market_b06 --no-create-info --skip-comments --skip-extended-insert --order-by-primary --hex-blob --skip-add-locks --skip-disable-keys --set-gtid-purged=OFF'],sensitive=True,timeout=180).stdout
 def financial(self,project):return hashlib.sha256(self.sql(project,FINANCIAL).encode()).hexdigest()
 def channels(self,project):return hashlib.sha256(self.sql(project,CHANNELS).encode()).hexdigest()
 def external(self):
  return {'hostsSha256':sha('C:/Windows/System32/drivers/etc/hosts'),'context':subprocess.check_output(['docker','context','show'],text=True).strip(),'shared':self.docker_run('shared-scope',['ps','-a','--filter','label=com.docker.compose.project!='+PROJECT,'--filter','label=com.docker.compose.project!='+self.clone,'--filter','label=b06.backup-tool!=true','--format','{{.ID}} {{.Names}} {{.Image}} {{.State}}']).stdout,'originalNetworks':self.docker_run('original-networks',['network','ls','--filter','label=com.docker.compose.project='+PROJECT,'--format','{{.ID}} {{.Name}}']).stdout}
 def preflight(self):
  self.d.capacity();self.d.ready();
  for path in HOME.glob('*/recovery.json'):
   require(path.parent==self.work or not json.loads(path.read_text()),'PENDING_BACKUP_RECOVERY')
  require(self.d.state()['mode']=='open' and self.d.state()['phase']=='READY','ORIGINAL_NOT_OPEN_READY')
  for f in (ROOT/'.local/b06/faults').glob('*/recovery.json'):require(json.loads(f.read_text())==[],'PENDING_FAULT_RECOVERY')
  owned={s:self.inspect(PROJECT,s) for s in SERVICES}
  require(all(v['State']['Running'] and v['State'].get('Health',{}).get('Status')=='healthy' for v in owned.values()),'UNHEALTHY_SOURCE')
  release=json.loads((ROOT/'docs/b06-fault-release.json').read_text(encoding='utf-8'));require(all(owned[s]['Image']==release['images'][k] for s,k in [('marketing-a','a'),('market-b','b'),('web','web')]),'UNTESTED_SOURCE_IMAGE')
  self.report['externalBefore']=self.external();self.report['sourceImages']={s:v['Image'] for s,v in owned.items()};self.report['sourceVolumes']={}
  for name in VOLUMES:
   vol=PROJECT+'_'+name;v=json.loads(self.docker_run('volume-identity',['volume','inspect',vol]).stdout)[0];require(v['Labels'].get('com.docker.compose.project')==PROJECT and v['Labels'].get('com.docker.compose.volume')==name,'VOLUME_OWNERSHIP_MISMATCH');self.report['sourceVolumes'][name]=vol
  self.check('source-ready-capacity-images-volumes-owned',True);self.save()
 def interrupt_original(self):
  owned={s:self.inspect(PROJECT,s) for s in SERVICES};self.journal={'restoreOriginal':True,'cloneProject':self.clone,'original':{s:{'id':v['Id'],'image':v['Image'],'restart':v['HostConfig']['RestartPolicy'],'volumes':{x['Destination']:x['Name'] for x in v['Mounts'] if x['Type']=='volume'}} for s,v in owned.items()},'phase':'BEFORE_GATE'};self.save()
  # The maintenance gateway still permits cancellation. Stop web, A and B to prove all writers are gone.
  self.d.configuration('maintenance');state=self.d.state();state.update(mode='maintenance',phase='B066_STOPPING');self.d.save(state);self.d.gateway('maintenance');self.journal['original']['web']['id']=self.inspect(PROJECT,'web')['Id'];self.save()
  for service in ['web','market-b','marketing-a','broker','namesrv','redis']:
   v=self.inspect(PROJECT,service);self.docker_run('disable-auto-restart-'+service,['update','--restart=no',v['Id']]);self.docker_run('graceful-stop-'+service,['stop','--time','90',v['Id']],timeout=120);v=self.inspect(PROJECT,service);self.check('normal-stopped-'+service,not v['State']['Running'] and not v['State']['OOMKilled'] and v['State']['ExitCode'] in [0,143])
  self.journal['phase']='WRITERS_STOPPED';self.report['originalFinancialBefore']=self.financial(PROJECT);self.report['originalChannelsBefore']=self.channels(PROJECT);self.save();self.event('all-application-and-mq-writers-stopped')
 def helper(self,label,volume,command,readonly=False):
  require(volume in {p+'_'+v for p in [PROJECT,self.clone] for v in VOLUMES},'UNOWNED_VOLUME')
  require(not volume.startswith(PROJECT+'_') or readonly,'ORIGINAL_VOLUME_MUST_BE_READ_ONLY')
  args=['run','--rm','--label','b06.backup-tool=true','--network','none','--memory','128m','--cpus','1','--pids-limit','64','--read-only','--cap-drop','ALL','--cap-add','CHOWN','--cap-add','DAC_OVERRIDE','--cap-add','FOWNER','--security-opt','no-new-privileges:true','--mount','type=volume,src='+volume+',dst=/volume'+(',readonly' if readonly else ''),'--mount','type=bind,src='+str(self.work)+',dst=/backup','--entrypoint','sh',HELPER,'-c',command]
  return self.docker_run(label,args,timeout=360)
 def stop_source_mysql(self):
  self.sql(PROJECT,'SET GLOBAL innodb_fast_shutdown=0;');v=self.inspect(PROJECT,'mysql');self.docker_run('mysql-no-restart',['update','--restart=no',v['Id']]);self.docker_run('mysql-slow-shutdown',['stop','--time','120',v['Id']],timeout=150);v=self.inspect(PROJECT,'mysql');self.check('mysql-normal-slow-shutdown',not v['State']['Running'] and v['State']['ExitCode']==0 and not v['State']['OOMKilled']);self.journal['phase']='COLD_POINT';self.report['consistentPointAt']=stamp();self.save()
 def snapshot(self):
  baseline=self.dump(PROJECT);(self.work/'business-before.sql').write_text(baseline,encoding='utf-8');self.report['financialBefore']=self.financial(PROJECT)
  # Preserve only an existing original, already applied signed event. No manufactured envelope.
  row=self.sql(PROJECT,"SELECT o.event_id,o.body_hash,HEX(o.body) FROM zj_market_b06.b_trade_outbox o WHERE o.event_type='PAYMENT_SUCCEEDED' AND o.state='DONE' AND EXISTS(SELECT 1 FROM group_buy_market_b06.ab_inbox i WHERE i.event_id=o.event_id AND i.processing_status='PROCESSED' AND i.outcome='APPLIED' AND i.body_hash=o.body_hash) ORDER BY o.event_id LIMIT 1;").strip().split('\t');require(len(row)==3,'NO_ORIGINAL_APPLIED_EVENT');raw=bytes.fromhex(row[2]);require(hashlib.sha256(raw).hexdigest()==row[1],'ORIGINAL_EVENT_HASH_MISMATCH');(self.work/'original-event.json').write_bytes(raw);self.report['replayedOriginalEvent']={'eventId':row[0],'bodySha256':row[1]}
  self.report['pendingAtPoint']=self.sql(PROJECT,"SELECT 'trade_inbox',state,COUNT(*) FROM zj_market_b06.b_trade_inbox GROUP BY state; SELECT 'trade_work',state,COUNT(*) FROM zj_market_b06.b_trade_work GROUP BY state;")
  self.stop_source_mysql()
  for s in SERVICES:require(not self.inspect(PROJECT,s)['State']['Running'],'WRITER_REAPPEARED')
  # Resolved compose includes capabilities, absolute binds and the exact original images.
  composed=json.loads(self.run('resolved-compose',self.d.compose+['-f',str(ROOT/'.local/b06/control/capabilities.yml'),'config','--format','json'],sensitive=True).stdout);bundle=self.work/'bundle';bundle.mkdir();mapping={}
  for folder in ['runtime','config','control','build','init','migrations']: (bundle/folder).mkdir()
  for src in [ROOT/'.local/b06/runtime',ROOT/'deploy/b06/config']:
   dst=bundle/('runtime' if src.name=='runtime' else 'config');shutil.copytree(src,dst,dirs_exist_ok=True)
   for f in src.rglob('*'):
    if f.is_file():mapping[str(f.resolve()).replace('\\','/').lower()]=str((dst/f.relative_to(src)).resolve())
  for name in ['state.json','deployment.properties','demo-accounts.json','seed-goods-id.txt','capabilities.properties']:
   src=ROOT/'.local/b06/control'/name;require(src.is_file(),'MISSING_CONTROL_FILE');shutil.copyfile(src,bundle/'control'/name);mapping[str(src.resolve()).replace('\\','/').lower()]=str((bundle/'control'/name).resolve())
  shutil.copytree(ROOT/'deploy/b06/init',bundle/'init',dirs_exist_ok=True);shutil.copytree(ROOT/'zj-market-infrastructure/src/main/resources/db/migration',bundle/'migrations',dirs_exist_ok=True);shutil.copyfile(ROOT/'deploy/b06/images.lock.json',bundle/'images.lock.json')
  for name in ['release.env','release-manifest.json']:shutil.copyfile(ROOT/'.local/b06/build'/name,bundle/'build'/name)
  for svc,config in composed['services'].items():
   if svc in self.report['sourceImages']:config['image']=self.report['sourceImages'][svc]
   for mount in config.get('volumes',[]):
    if mount['type']=='bind':
     key=str(Path(mount['source']).resolve()).replace('\\','/').lower();require(key in mapping,'UNBACKED_BIND');mount['source']=mapping[key]
  for config in composed['secrets'].values():
   key=str(Path(config['file']).resolve()).replace('\\','/').lower();require(key in mapping,'UNBACKED_SECRET');config['file']=mapping[key]
  atomic(self.work/'compose-snapshot.json',composed);atomic(self.work/'state-before.json',self.d.state());shutil.copyfile(ROOT/'.local/b06/build/recovery-tools/release.json',self.work/'recovery-tools.json')
  for name in VOLUMES:self.helper('cold-archive-'+name,PROJECT+'_'+name,'tar --numeric-owner -cpf /backup/'+name+'.tar -C /volume .',readonly=True);self.check('cold-archive-'+name,(self.work/(name+'.tar')).stat().st_size>0)
  helper_id=json.loads(self.docker_run('helper-immutable-id',['image','inspect',HELPER]).stdout)[0]['Id']
  ids=sorted(set(self.report['sourceImages'].values())|{self.d.state()['maintenanceImage'],self.d.state()['sdkImage'],helper_id,json.loads((self.work/'recovery-tools.json').read_text())['candidate']['id'],json.loads((self.work/'recovery-tools.json').read_text())['replay']['id']});self.docker_run('immutable-images-export',['image','save','-o',str(self.work/'images.tar'),*ids],timeout=600)
  files={str(f.relative_to(self.work)).replace('\\','/'):sha(f) for f in bundle.rglob('*') if f.is_file()}
  for name in ['business-before.sql','original-event.json','compose-snapshot.json','state-before.json','recovery-tools.json','images.tar']+[n+'.tar' for n in VOLUMES]:files[name]=sha(self.work/name)
  manifest={'format':2,'project':PROJECT,'runName':self.name,'consistentPointAt':self.report['consistentPointAt'],'volumes':list(VOLUMES),'files':files,'images':ids,'financialSha256':self.report['financialBefore'],'businessDumpSha256':sha(self.work/'business-before.sql'),'schemaFingerprint':self.d.state()['schemaFingerprint'],'migrationHistoryHash':self.d.state()['migrationHistoryHash'],'secretProtection':'private local NTFS ACL; not encrypted/off-host','rpoScope':'only the fully stopped consistency point; subsequent original transactions excluded'};atomic(self.work/'manifest.json',manifest);atomic(self.work/'COMPLETE.json',{'manifestSha256':sha(self.work/'manifest.json'),'completedAt':stamp()});validate_manifest(self.work);self.event('cold-backup-complete',bytes=sum((self.work/n).stat().st_size for n in files));self.check('complete-set-hash-verified',True)
 def clone_config(self):return self.work/'restore-compose.json'
 def compose(self):return self.docker+['compose','-p',self.clone,'-f',str(self.clone_config())]
 def restore(self):
  m=validate_manifest(self.work);self.check('backup-complete-and-all-hashes-before-restore',True)
  require(not self.docker_run('restore-project-absent',['ps','-a','--filter','label=com.docker.compose.project='+self.clone,'--format','{{.ID}}']).stdout.strip(),'RESTORE_PROJECT_EXISTS')
  self.journal['phase']='CREATING_RESTORE';self.save()
  for name in VOLUMES:
   volume=self.clone+'_'+name;require(not self.docker_run('restore-volume-absent',['volume','ls','--filter','name=^'+volume+'$','--format','{{.Name}}']).stdout.strip(),'RESTORE_VOLUME_EXISTS');self.docker_run('create-empty-volume',['volume','create','--label','com.docker.compose.project='+self.clone,'--label','com.docker.compose.volume='+name,'--label','b06.backup.batch='+self.name,volume]);self.helper('assert-empty-'+name,volume,'test -z "$(ls -A /volume)"');self.helper('extract-'+name,volume,'tar --numeric-owner -xpf /backup/'+name+'.tar -C /volume');self.helper('verify-extracted-'+name,volume,'tar --compare --numeric-owner -f /backup/'+name+'.tar -C /volume',readonly=True);self.check('empty-volume-restored-byte-metadata-'+name,True)
  self.docker_run('archived-images-load',['image','load','-i',str(self.work/'images.tar')],timeout=600)
  for ident in m['images']:require(json.loads(self.docker_run('restored-image-id',['image','inspect',ident]).stdout)[0]['Id']==ident,'ARCHIVED_IMAGE_MISMATCH')
  config=json.loads((self.work/'compose-snapshot.json').read_text());config['name']=self.clone
  isolated_networks(config,self.clone)
  require(all(v['name'].startswith(self.clone+'_') for v in config['networks'].values()),'RESTORE_NETWORK_SCOPE')
  shutil.copytree(self.work/'bundle',self.work/'restore-files')
  for svc in config['services'].values():
   for mount in svc.get('volumes',[]):
    if mount['type']=='bind':mount['source']=str(Path(mount['source']).relative_to(self.work/'bundle'));mount['source']=str(self.work/'restore-files'/mount['source'])
  for secret in config['secrets'].values():secret['file']=str(self.work/'restore-files'/Path(secret['file']).relative_to(self.work/'bundle'))
  for name in VOLUMES:config['volumes'][name]={'external':True,'name':self.clone+'_'+name}
  for v in config['services'].values():v.pop('container_name',None);v.get('labels',{}).pop('com.docker.compose.project',None)
  # Never expose the restored write entry before full schema/data/financial checks.
  for mount in config['services']['web']['volumes']:
   if mount['target']=='/etc/b06/admission.conf':mount['source']=str(self.work/'restore-files/config/admission-maintenance.conf')
  atomic(self.clone_config(),config);self.run('restore-middleware',self.compose()+['up','-d','--wait','--wait-timeout','180','mysql','redis','namesrv','broker'],timeout=240)
  for service in ['mysql','redis','namesrv','broker']:
   v=self.inspect(self.clone,service);require(all(name.startswith(self.clone+'_') for name in v['NetworkSettings']['Networks']),'RESTORE_JOINED_ORIGINAL_NETWORK')
  self.check('actual-restore-middleware-networks-isolated',True)
  self.report['restoredChannelsBeforeWorkers']=self.channels(self.clone);self.save()
  after=self.dump(self.clone);self.check('all-a-b-tables-and-flyway-exact-after-empty-volume-restore',after==(self.work/'business-before.sql').read_text(encoding='utf-8'));self.check('funds-inventory-ledgers-quotas-inbox-exact-before-workers',self.financial(self.clone)==m['financialSha256'])
  # Reuse original validator with explicit isolated project/control/runtime and resolved compose.
  repo=self.work/'restore-files/repo';(repo/'deploy/b06').mkdir(parents=True);shutil.copytree(self.work/'restore-files/init',repo/'deploy/b06/init');shutil.copytree(self.work/'restore-files/migrations',repo/'zj-market-infrastructure/src/main/resources/db/migration');shutil.copytree(self.work/'restore-files/config',repo/'deploy/b06/config');shutil.copyfile(self.work/'restore-files/images.lock.json',repo/'deploy/b06/images.lock.json')
  mod=module('deployment_clone',ROOT/'scripts/b06-deployment.py');mod.ROOT=repo;mod.PROJECT=self.clone;mod.CONTROL=self.work/'restore-files/control';mod.RUNTIME=self.work/'restore-files/runtime';mod.BUILD=self.work/'bundle/build';state=json.loads((mod.CONTROL/'state.json').read_text());state['project']=self.clone;atomic(mod.CONTROL/'state.json',state);self.cd=mod.Deployment('desktop-linux');self.cd.compose=self.compose();self.cd.ready();self.check('restored-schema-history-minimal-grants-locked-migrators',True);self.cd.configuration('open')
  self.run('restore-applications',self.compose()+['up','-d','--wait','--wait-timeout','180','marketing-a','market-b','web'],timeout=240);self.client_ready();self.check('strict-https-identity-product-sync-signed-rpc-after-restore',True);self.check('restored-financials-stable-after-original-workers',self.financial(self.clone)==m['financialSha256']);self.event('restored-full-stack-ready')
  self.gateway('open');self.run('restored-new-order-actual-checkout',['node',ROOT/'docs/tests/b06-startup-client.mjs','hold',self.work/'restore-files/control',self.work/'restore-files/runtime'],timeout=150);self.run('restored-new-order-cancel',['node',ROOT/'docs/tests/b06-startup-client.mjs','cancel',self.work/'restore-files/control',self.work/'restore-files/runtime'],timeout=90);self.run('restored-new-order-closed',['node',ROOT/'docs/tests/b06-startup-client.mjs','closed',self.work/'restore-files/control',self.work/'restore-files/runtime'],timeout=150);self.check('restored-new-purchase-checkout-and-cancel-close-release',True);self.check('actual-channel-money-and-original-requests-stable-after-restored-workers',self.channels(self.clone)==self.report['restoredChannelsBeforeWorkers'])
 def client_ready(self):return self.run('strict-client-readiness',['node',ROOT/'docs/tests/b06-startup-client.mjs','ready',self.work/'restore-files/control',self.work/'restore-files/runtime'],timeout=150)
 def gateway(self,mode):
  config=json.loads(self.clone_config().read_text())
  for mount in config['services']['web']['volumes']:
   if mount['target']=='/etc/b06/admission.conf':mount['source']=str(self.work/('restore-files/config/admission-'+mode+'.conf'))
  atomic(self.clone_config(),config);self.run('restore-gateway-'+mode,self.compose()+['up','-d','--no-deps','--force-recreate','--wait','--wait-timeout','90','web'],timeout=120)
 def replay(self):
  values=json.loads((self.work/'bundle/runtime/private/values.json').read_text());materials=self.work/'replay';materials.mkdir();(materials/'probe.properties').write_text(''.join(k+'='+values[k]+'\n' for k in ['mq_admin','mq_b']));shutil.copyfile(self.work/'original-event.json',materials/'original-event.json');shutil.copyfile(self.work/'bundle/runtime/mq.pem',materials/'mq.pem');tool=json.loads((self.work/'recovery-tools.json').read_text())['replay']['id'];before=self.financial(self.clone)
  args=['run','--rm','--label','b06.backup-tool=true','--network',self.clone+'_mq','--memory','320m','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,nosuid,size=32m','--mount','type=bind,src='+str(materials)+',dst=/test,readonly','--mount','type=bind,src='+str(materials)+',dst=/run/secrets,readonly','--mount','type=bind,src='+str(self.work/'bundle/config/mq-tls-client.properties')+',dst=/etc/b06/mq-tls.properties,readonly','--entrypoint','java',tool,'-Xmx192m','-Duser.home=/tmp','-Dtls.enable=true','-Dtls.test.mode.enable=false','-Dtls.client.authServer=true','-Dtls.config.file=/etc/b06/mq-tls.properties','-cp','/tools/classes:/tools/libs/*','RecoveryReplayProbe',self.report['replayedOriginalEvent']['bodySha256']]
  out=self.docker_run('actual-original-event-replay-consumed',args,timeout=110).stdout;self.check('original-signed-event-two-deliveries-actually-consumed','RECOVERY_REPLAY_PASS' in out);self.check('original-duplicate-no-new-charge-refund-stock-quota-or-inbox',self.financial(self.clone)==before);self.check('original-replay-actual-channel-money-and-request-facts-stable',self.channels(self.clone)==self.report['restoredChannelsBeforeWorkers'])
 def release_test(self):
  state=json.loads((self.work/'state-before.json').read_text());release=json.loads((self.work/'recovery-tools.json').read_text());jar=release['businessJarSha256'];compatible(release,state,jar);before=self.financial(self.clone);config=json.loads(self.clone_config().read_text());original=config['services']['market-b']['image'];require(original==release['rollbackImage'],'ROLLBACK_BASELINE_MISMATCH')
  for image in [original,release['candidate']['id']]:
   result=self.docker_run('business-jar-proof',['run','--rm','--label','b06.backup-tool=true','--network','none','--memory','32m','--entrypoint','sha256sum',image,'/app/app.jar']).stdout;self.check('candidate-and-rollback-original-business-jar',result.split()[0]==jar,image=image)
  configs=[json.loads(self.docker_run('runtime-contract-image',['image','inspect',img]).stdout)[0]['Config'] for img in [original,release['candidate']['id']]]
  self.check('compatible-package-runtime-contract-preserved',all(configs[0].get(k)==configs[1].get(k) for k in ['Entrypoint','Cmd','Env','User','WorkingDir','Healthcheck','ExposedPorts']))
  bad=dict(release,protocol='unverified-old-protocol')
  try:compatible(bad,state,jar)
  except RuntimeError:self.check('incompatible-release-refused-before-mutation',True)
  else:raise RuntimeError('INCOMPATIBLE_ACCEPTED')
  self.gateway('maintenance');config=json.loads(self.clone_config().read_text());config['services']['market-b']['image']=release['candidate']['id'];atomic(self.clone_config(),config);self.event('compatible-candidate-switch-start');self.run('deploy-compatible-candidate',self.compose()+['up','-d','--no-deps','--force-recreate','--wait','--wait-timeout','150','market-b'],timeout=180);self.client_ready();self.gateway('open');self.check('distinct-compatible-candidate-opened',self.inspect(self.clone,'market-b')['Image']==release['candidate']['id']);self.event('compatible-candidate-opened')
  # A rejected health check must never reopen the gate. Failure exists only in this clone overlay.
  self.gateway('maintenance');config=json.loads(self.clone_config().read_text());health=config['services']['market-b']['healthcheck'];config['services']['market-b']['healthcheck']={'test':['CMD','sh','-c','exit 1'],'interval':'2s','timeout':'1s','retries':2,'start_period':'1s'};atomic(self.clone_config(),config)
  failed=self.run('candidate-health-failure-closed',self.compose()+['up','-d','--no-deps','--force-recreate','--wait','--wait-timeout','25','market-b'],timeout=40,ok=False);self.check('unhealthy-release-refused-with-gate-closed',failed.returncode!=0);self.run('actual-closed-gateway',['node',ROOT/'docs/tests/b06-recovery-gate.mjs',self.work/'restore-files/runtime'],timeout=60);self.check('failure-gate-actual-https-mutations-rejected',True)
  config['services']['market-b']['image']=original;config['services']['market-b']['healthcheck']=health;atomic(self.clone_config(),config);self.event('rollback-start');self.run('rollback-original-compatible-image',self.compose()+['up','-d','--no-deps','--force-recreate','--wait','--wait-timeout','150','market-b'],timeout=180);self.cd.ready();self.client_ready();self.check('rollback-restores-exact-original-image-and-funds',self.inspect(self.clone,'market-b')['Image']==original and self.financial(self.clone)==before);self.check('rollback-actual-channel-money-and-original-facts-stable',self.channels(self.clone)==self.report['restoredChannelsBeforeWorkers']);self.gateway('open');self.event('rollback-original-opened');self.report['releaseImages']={'candidate':release['candidate']['id'],'rollback':original};self.check('rollback-schema-history-unchanged-no-downgrade',self.cd.history()==state['migrationHistoryHash'] and self.cd.fingerprint()==state['schemaFingerprint'])
 def recover(self):
  if not self.journal:return
  # Stop only our restore project; never delete its volumes or the original volumes.
  cloneids=self.docker_run('clone-owned-containers',['ps','-a','--filter','label=com.docker.compose.project='+self.clone,'--format','{{.ID}}']).stdout.split()
  if cloneids:self.docker_run('stop-isolated-restore',['stop','--time','90',*cloneids],timeout=180)
  if self.journal.get('restoreOriginal'):
   for service,baseline in self.journal['original'].items():
    v=self.inspect(PROJECT,service);require(v['Image']==baseline['image'],'ORIGINAL_IMAGE_DRIFT');require({x['Destination']:x['Name'] for x in v['Mounts'] if x['Type']=='volume'}==baseline['volumes'],'ORIGINAL_VOLUME_DRIFT')
    if service not in ['web','market-b']:require(v['Id']==baseline['id'],'ORIGINAL_CONTAINER_REPLACED')
    policy=baseline['restart'];value=policy['Name']+(':'+str(policy['MaximumRetryCount']) if policy['Name']=='on-failure' and policy['MaximumRetryCount'] else '');self.docker_run('restore-original-restart-'+service,['update','--restart='+value,v['Id']])
   self.journal['phase']='ORIGINAL_CONTROLLED_OPEN';self.save();self.d.start('open');self.check('original-restored-open-ready',self.d.state()['mode']=='open' and self.d.state()['phase']=='READY')
   expected=self.report.get('originalFinancialBefore') or self.report.get('financialBefore')
   if expected:self.check('original-funds-stock-quotas-inbox-preserved',self.financial(PROJECT)==expected)
   if self.report.get('originalChannelsBefore'):self.check('original-actual-channel-funds-and-request-hashes-preserved',self.channels(PROJECT)==self.report['originalChannelsBefore'])
  if 'externalBefore' in self.report:self.check('hosts-shared-containers-context-original-networks-unchanged',self.external()==self.report['externalBefore'])
  self.journal={};self.report['originalRecovered']=True;self.report['originalRecoveredAt']=stamp();self.save();self.event('original-service-restored')
 def execute_restore(self,source_name):
  valid_name(source_name);source=HOME/source_name
  try:
   m=validate_manifest(source);require(source!=self.work,'RESTORE_MUST_USE_FRESH_BATCH');self.preflight();require(m['schemaFingerprint']==self.d.state()['schemaFingerprint'] and m['migrationHistoryHash']==self.d.state()['migrationHistoryHash'],'BACKUP_INCOMPATIBLE_WITH_CURRENT_RELEASE');self.interrupt_original();self.stop_source_mysql();self.report['originalQuiescedAt']=self.report['consistentPointAt']
   for name in m['files']:
    target=self.work/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
   config=json.loads((self.work/'compose-snapshot.json').read_text())
   for svc in config['services'].values():
    for mount in svc.get('volumes',[]):
     if mount['type']=='bind':mount['source']=str(self.work/'bundle'/Path(mount['source']).relative_to(source/'bundle'))
   for secret in config['secrets'].values():secret['file']=str(self.work/'bundle'/Path(secret['file']).relative_to(source/'bundle'))
   atomic(self.work/'compose-snapshot.json',config);m['sourceBackupManifestSha256']=sha(source/'manifest.json');m['sourceBackupRunName']=source_name;m['runName']=self.name;m['files']['compose-snapshot.json']=sha(self.work/'compose-snapshot.json');atomic(self.work/'manifest.json',m);atomic(self.work/'COMPLETE.json',{'manifestSha256':sha(self.work/'manifest.json'),'completedAt':stamp()});raw=(self.work/'original-event.json').read_bytes();self.report.update(financialBefore=m['financialSha256'],consistentPointAt=m['consistentPointAt'],sourceBackupRunName=source_name,replayedOriginalEvent={'eventId':json.loads(raw)['eventId'],'bodySha256':hashlib.sha256(raw).hexdigest()});self.save()
   self.restore();self.replay();self.release_test();self.report['status']='VALIDATED_PENDING_ORIGINAL_RECOVERY'
  except Exception as e:self.report.update(status='FAILED',error=type(e).__name__+': '+str(e));self.save();raise
  finally:
   if self.journal:
    try:self.recover()
    except Exception as e:self.report.update(status='RECOVERY_REQUIRED',recoveryError=type(e).__name__+': '+str(e));self.save();raise
  self.report.update(status='PASSED',finishedAt=stamp());self.save();print('B066_EXISTING_BACKUP_RESTORE_PASS',flush=True)
 def execute(self,backup_only=False):
  try:
   self.preflight();self.interrupt_original();self.snapshot()
   if not backup_only:self.restore();self.replay();self.release_test()
   self.report['status']='VALIDATED_PENDING_ORIGINAL_RECOVERY';self.report['finishedAt']=stamp();self.save()
  except Exception as e:self.report.update(status='FAILED',error=type(e).__name__+': '+str(e));self.save();raise
  finally:
   if self.journal:
    try:self.recover()
    except Exception as e:self.report.update(status='RECOVERY_REQUIRED',recoveryError=type(e).__name__+': '+str(e));self.save();raise
  self.report.update(status='BACKUP_COMPLETE' if backup_only else 'PASSED',finishedAt=stamp());self.save();print('B066_'+self.report['status'],flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['run','backup','verify','restore','recover']);p.add_argument('--run-name',required=True);p.add_argument('--from-backup');a=p.parse_args();valid_name(a.run_name)
 if a.action=='restore':require(a.from_backup is not None,'SOURCE_BACKUP_REQUIRED');valid_name(a.from_backup)
 if a.action=='verify':validate_manifest(HOME/a.run_name);print('B066_BACKUP_HASHES_PASS');return
 faults=module('fault_lock',ROOT/'scripts/b06-faults.py');obs=module('observation_lock',ROOT/'scripts/b06-observability.py')
 with faults.deployment_lock(),obs.exclusive():
  r=Recovery(a.run_name,existing=a.action=='recover')
  if a.action=='recover':r.recover();print('B066_RECOVERY_PASS')
  elif a.action=='restore':r.execute_restore(a.from_backup)
  else:r.execute(backup_only=a.action=='backup')
if __name__=='__main__':main()
