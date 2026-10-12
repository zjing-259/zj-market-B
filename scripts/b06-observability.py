"""Local B064 observer. Ordinary sampling is SELECT-only; no public endpoint or business mutation."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, contextlib, importlib.util, json, os, re, secrets, subprocess, time
ROOT=Path(__file__).resolve().parents[1]
HOME=ROOT/'.local/b06/observability'
RUNTIME=ROOT/'.local/b06/runtime'
PROJECT='zj-market-b06'
SERVICES=('mysql','redis','namesrv','broker','marketing-a','market-b','web')
B='zj_market_b06'; A='group_buy_market_b06'
# (schema, table, state, terminal states, review predicate, due ms, created ms, failures, lease ms)
QUEUES=(
 (B,'b_payment_task','state',"'DONE'","state='REVIEW_REQUIRED'",'next_attempt_ms',"(SELECT created_at_ms FROM zj_market_b06.b_payment p WHERE p.payment_id=q.payment_id)",'failure_count','lease_until_ms'),
 (B,'b_trade_coordination','run_state',"'DONE'","run_state='REVIEW_REQUIRED' OR paused=1",'next_attempt_ms',"(SELECT created_at_ms FROM zj_market_b06.b_market_order o WHERE o.order_id=q.order_id)",'failure_count','lease_until_ms'),
 (B,'b_trade_work','state',"'DONE'","state='REVIEW_REQUIRED'",'next_attempt_ms','created_at_ms','failure_count','lease_until_ms'),
 (B,'b_trade_inbox','state',"'DONE'","state='REVIEW_REQUIRED'",'next_attempt_ms','created_at_ms','0','NULL'),
 (B,'b_trade_outbox','state',"'DONE'","state='REVIEW_REQUIRED'",'next_attempt_ms','created_at_ms','failure_count','lease_until_ms'),
 (B,'b_sim_notification','state',"'DONE'","state='REVIEW_REQUIRED'",'next_attempt_ms','created_at_ms','failure_count','lease_until_ms'),
 (B,'b_reconciliation_task','state',"'RESOLVED'","state='REVIEW_REQUIRED'",'next_attempt_ms','created_at_ms','failure_count','lease_until_ms'),
 (B,'b_refund_task','state',"'DONE'","state='REVIEW_REQUIRED'",'next_attempt_ms','created_at_ms','failure_count','lease_until_ms'),
 (B,'b_sim_refund_notification','state',"'DONE'","state='REVIEW_REQUIRED'",'next_attempt_ms','created_at_ms','failure_count','lease_until_ms'),
 (B,'b_product_outbox','processing_state',"'CONFIRMED','REJECTED','SUPERSEDED'","paused=1","CASE WHEN delivery_state='PENDING' AND send_attempts=0 THEN next_send_ms WHEN delivery_state='PENDING' THEN LEAST(next_send_ms,next_query_ms) ELSE next_query_ms END",'created_at_ms','send_failures','NULLIF(lease_until_ms,0)'),
 (A,'ab_outbox','status',"'PUBLISHED'","status='REVIEW_REQUIRED'",'UNIX_TIMESTAMP(next_attempt_at)*1000','UNIX_TIMESTAMP(created_at)*1000','NULL','UNIX_TIMESTAMP(lease_until)*1000'),
 (A,'ab_waiting_dependency',"'WAITING'","'NONE'",'FALSE','UNIX_TIMESTAMP(next_check_at)*1000','NULL','NULL','NULL'),
)
TABLES={B:{x[1] for x in QUEUES if x[0]==B}|{'b_market_order','b_payment','b_refund','b_inventory_account','b_inventory_reservation','b_inventory_ledger','b_fulfillment','b_trade_quarantine','b_sync_quarantine','b_order_block'},
 A:{x[1] for x in QUEUES if x[0]==A}|{'ab_trade_order','ab_team','ab_quarantine'}}

# A late team notice can persist after the original reconciliation/refund has finished.
# Retain the row; classify it only when its original binding and all terminal facts agree.
def historical_team_handoff_sql():
 return """q.state='DEFERRED_B05' AND q.kind IN ('TEAM_FAILED','TEAM_RECONCILIATION_REQUIRED')
 AND q.lease_token IS NULL AND q.lease_until_ms IS NULL AND q.evidence_hash=SHA2(q.evidence,256)
 AND EXISTS(SELECT 1 FROM zj_market_b06.b_market_order o
 JOIN zj_market_b06.b_payment p ON p.order_id=o.order_id
 JOIN zj_market_b06.b_refund r ON r.order_id=o.order_id AND r.payment_id=p.payment_id
 JOIN zj_market_b06.b_inventory_reservation i ON i.order_id=o.order_id
 JOIN zj_market_b06.b_reconciliation_task t ON t.team_id=q.team_id
 WHERE o.order_id=q.order_id AND o.business_status='CLOSED'
 AND JSON_UNQUOTE(JSON_EXTRACT(o.a_evidence,'$.teamId'))=q.team_id
 AND t.source=JSON_UNQUOTE(JSON_EXTRACT(o.a_evidence,'$.source'))
 AND t.channel=JSON_UNQUOTE(JSON_EXTRACT(o.a_evidence,'$.channel')) AND t.state='RESOLVED'
 AND JSON_UNQUOTE(JSON_EXTRACT(CONVERT(q.evidence USING utf8mb4),'$.source'))=t.source
 AND JSON_UNQUOTE(JSON_EXTRACT(CONVERT(q.evidence USING utf8mb4),'$.channel'))=t.channel
 AND JSON_UNQUOTE(JSON_EXTRACT(CONVERT(q.evidence USING utf8mb4),'$.payload.teamId'))=q.team_id
 AND p.funds_state='SUCCEEDED' AND p.a_acceptance='ACCEPTED'
 AND r.amount=p.amount AND r.funds_status='SUCCEEDED' AND r.sync_status='ACCEPTED' AND r.release_status='RELEASED'
 AND i.state='RELEASED'
 AND (SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='RELEASE')=1
 AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='CONFIRM')
 AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_fulfillment f WHERE f.order_id=o.order_id)
 AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_order_block k WHERE k.order_id=o.order_id AND k.state='ACTIVE' AND k.kind<>'RECONCILIATION')
 AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_trade_work w WHERE w.order_id=o.order_id AND w.state='REVIEW_REQUIRED'))"""

def stamp():return datetime.now(timezone.utc).isoformat()
def load(name,default=None):
 p=HOME/name
 return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

def atomic(name,data):
 p=HOME/name;t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');t.replace(p)

def append(name,data,limit=2*1024*1024,backups=3):
 p=HOME/name
 if p.exists() and p.stat().st_size>=limit:
  (HOME/(name+'.'+str(backups))).unlink(missing_ok=True)
  for n in range(backups-1,0,-1):
   old=HOME/(name+'.'+str(n))
   if old.exists():old.replace(HOME/(name+'.'+str(n+1)))
  p.replace(HOME/(name+'.1'))
 with p.open('a',encoding='utf-8') as f:f.write(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n');f.flush();os.fsync(f.fileno())

@contextlib.contextmanager
def exclusive():
 HOME.mkdir(parents=True,exist_ok=True)
 with (HOME/'observer.lock').open('a+b') as f:
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

def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class Observer:
 def __init__(self,context='desktop-linux'):
  self.docker=['docker','--context',context]
  self.image=json.loads((ROOT/'deploy/b06/images.lock.json').read_text(encoding='utf-8'))['mysql']
 def command(self,args,sql=None,timeout=45):
  r=subprocess.run([str(x) for x in args],input=sql,capture_output=True,text=True,encoding='utf-8',errors='strict',timeout=timeout)
  if r.returncode:raise RuntimeError('COMMAND_FAILED_'+str(r.returncode)) # no raw driver errors/secrets
  return r.stdout
 def ownership(self):
  v=self.command(self.docker+['inspect','--format','{{index .Config.Labels "com.docker.compose.project"}}',PROJECT+'-mysql-1']).strip()
  if v!=PROJECT:raise RuntimeError('OWNERSHIP_MISMATCH')
 def sql(self,query,extra=()):
  if not (HOME/'mysql.cnf').exists():raise RuntimeError('OBSERVER_NOT_INITIALIZED')
  return self.command(self.docker+['run','--rm','-i','--label','b06.observer=true','--network',PROJECT+'_data','--memory','96m','--cpus','0.5','--pids-limit','64','--read-only','--tmpfs','/tmp:rw,nosuid,size=8m','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges:true','--mount','type=bind,src='+str(HOME/'mysql.cnf')+',dst=/observer/client.cnf,readonly','--mount','type=bind,src='+str(RUNTIME/'mysql-ca.pem')+',dst=/observer/ca.pem,readonly','--entrypoint','sh',self.image,'-c','cp /observer/client.cnf /tmp/client.cnf && chmod 600 /tmp/client.cnf && exec mysql --defaults-extra-file=/tmp/client.cnf --batch --raw --skip-column-names --connect-timeout=5 "$@"','b06-observer',*extra],query)
 def setup(self):
  self.ownership()
  receipt=load('principal.json')
  d=module('deployment',ROOT/'scripts/b06-deployment.py').Deployment(self.docker[-1]);d.state()
  if receipt is None:
   if d.admin('observer-existing-user',"SELECT User FROM mysql.user WHERE User='b06_observer';").strip():raise RuntimeError('UNOWNED_OBSERVER_ACCOUNT')
   receipt={'project':PROJECT,'user':'b06_observer','password':secrets.token_hex(32),'createdAt':stamp()};atomic('principal.json',receipt)
  if receipt.get('project')!=PROJECT or receipt.get('user')!='b06_observer':raise RuntimeError('OBSERVER_RECEIPT_MISMATCH')
  password=receipt['password'];d.values['observer']=password
  d.admin('observer-principal',"CREATE USER IF NOT EXISTS 'b06_observer'@'%' IDENTIFIED BY '"+password+"' REQUIRE SSL;")
  d.admin('observer-grants',''.join("GRANT SELECT ON "+schema+'.'+t+" TO 'b06_observer'@'%';\n" for schema,tables in TABLES.items() for t in sorted(tables)))
  (HOME/'mysql.cnf').write_text('[client]\nuser=b06_observer\npassword='+password+'\nhost=mysql\nssl-mode=VERIFY_IDENTITY\nssl-ca=/observer/ca.pem\ndefault-character-set=utf8mb4\n',encoding='utf-8')
  actual=self.sql('SHOW GRANTS FOR CURRENT_USER();').splitlines()
  expected={"GRANT SELECT ON `"+s+'`.`'+t+"` TO `b06_observer`@`%`" for s,ts in TABLES.items() for t in ts}
  actual_tables={v for v in actual if v.startswith('GRANT SELECT ')}
  if actual_tables!=expected or len(actual)!=len(expected)+1 :raise RuntimeError('OBSERVER_GRANTS_MISMATCH')
  if d.admin('observer-require-ssl',"SELECT ssl_type FROM mysql.user WHERE User='b06_observer' AND Host='%';").strip()!='ANY':raise RuntimeError('OBSERVER_SSL_REQUIRED')
  atomic('grant-proof.json',{'at':stamp(),'tables':{s:sorted(ts) for s,ts in TABLES.items()},'selectOnly':True,'requireSsl':True})
 def metrics_sql(self):
  queries=["SET SESSION time_zone='+00:00'; SET SESSION max_execution_time=5000; START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY; SET @now=CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS UNSIGNED);", "SELECT JSON_OBJECT('kind','clock','databaseNowMs',@now);", "SHOW SESSION STATUS LIKE 'Ssl_cipher';"]
  for schema,table,state,terminal,review,due,created,failures,lease in QUEUES:
   active=f'{state} NOT IN ({terminal})';historical=historical_team_handoff_sql() if table=='b_trade_work' else 'FALSE'
   if table=='b_trade_work':active=f'({active}) AND NOT COALESCE(({historical}),FALSE)'
   due_pred=f'({active}) AND NOT ({review}) AND ({due})<=@now'
   queries.append(f"SELECT JSON_OBJECT('kind','queue','queue','{table}','pending',COALESCE(SUM({active}),0),'historicalSettledHandoffs',COALESCE(SUM({historical}),0),'due',COALESCE(SUM({due_pred}),0),'oldestPendingSeconds',{'NULL' if created=='NULL' else 'COALESCE(MAX(IF('+active+',GREATEST(0,@now-('+created+'))/1000,NULL)),0)'},'oldestOverdueSeconds',COALESCE(MAX(IF({due_pred},GREATEST(0,@now-({due}))/1000,NULL)),0),'review',COALESCE(SUM({review}),0),'recordedFailures',{'NULL' if failures=='NULL' else 'COALESCE(SUM('+failures+'),0)'},'recordedRetries',{'COALESCE(SUM(GREATEST(attempts-1,0)),0)' if table=='ab_outbox' else 'NULL'},'recordedDependencyChecks',{'COALESCE(SUM(attempts),0)' if table=='ab_waiting_dependency' else 'NULL'},'expiredLeases',COALESCE(SUM(({active}) AND ({lease}) IS NOT NULL AND ({lease})<=@now),0),'ageAvailable',{'false' if created=='NULL' else 'true'}) FROM {schema}.{table} q;")
  queries.append("SELECT JSON_OBJECT('kind','obligations','paymentAwaitingA',(SELECT COUNT(*) FROM zj_market_b06.b_payment WHERE funds_state='SUCCEEDED' AND a_acceptance<>'ACCEPTED'),'paymentAwaitingAOldestSeconds',(SELECT COALESCE(MAX(GREATEST(0,@now-paid_at_ms)/1000),0) FROM zj_market_b06.b_payment WHERE funds_state='SUCCEEDED' AND a_acceptance<>'ACCEPTED'),'refundUnfinished',(SELECT COUNT(*) FROM zj_market_b06.b_refund WHERE funds_status<>'SUCCEEDED' OR sync_status<>'ACCEPTED' OR release_status<>'RELEASED'),'refundUnfinishedOldestSeconds',(SELECT COALESCE(MAX(GREATEST(0,@now-created_at_ms)/1000),0) FROM zj_market_b06.b_refund WHERE funds_status<>'SUCCEEDED' OR sync_status<>'ACCEPTED' OR release_status<>'RELEASED'),'activePaymentReview',(SELECT COUNT(*) FROM zj_market_b06.b_payment p JOIN zj_market_b06.b_market_order o ON o.order_id=p.order_id WHERE p.review_required=1 AND NOT(o.business_status='CLOSED' AND p.last_error IN ('TEAM_FAILED','TEAM_RECONCILIATION_REQUIRED') AND EXISTS(SELECT 1 FROM zj_market_b06.b_refund r WHERE r.payment_id=p.payment_id AND r.amount=p.amount AND r.funds_status='SUCCEEDED' AND r.sync_status='ACCEPTED' AND r.release_status='RELEASED') AND EXISTS(SELECT 1 FROM zj_market_b06.b_inventory_reservation i WHERE i.order_id=o.order_id AND i.state='RELEASED') AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_order_block k WHERE k.order_id=o.order_id AND k.state='ACTIVE' AND k.kind<>'RECONCILIATION') AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_trade_work w WHERE w.order_id=o.order_id AND w.state='REVIEW_REQUIRED'))),'activeOrderReview',(SELECT COUNT(*) FROM zj_market_b06.b_market_order o WHERE o.review_required=1 AND NOT(o.business_status='CLOSED' AND o.last_error IN ('TEAM_FAILED','TEAM_RECONCILIATION_REQUIRED') AND EXISTS(SELECT 1 FROM zj_market_b06.b_inventory_reservation i WHERE i.order_id=o.order_id AND i.state='RELEASED') AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_order_block k WHERE k.order_id=o.order_id AND k.state='ACTIVE' AND k.kind<>'RECONCILIATION') AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_trade_work w WHERE w.order_id=o.order_id AND w.state='REVIEW_REQUIRED') AND EXISTS(SELECT 1 FROM zj_market_b06.b_refund r JOIN zj_market_b06.b_payment p ON p.payment_id=r.payment_id WHERE r.order_id=o.order_id AND r.amount=p.amount AND r.funds_status='SUCCEEDED' AND r.sync_status='ACCEPTED' AND r.release_status='RELEASED') OR (o.business_status='CLOSED' AND o.last_error IN ('TEAM_FAILED','TEAM_RECONCILIATION_REQUIRED') AND o.close_basis='A_CONFIRMED' AND o.payment_exposure='NEVER_OPENED' AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id) AND EXISTS(SELECT 1 FROM zj_market_b06.b_inventory_reservation i WHERE i.order_id=o.order_id AND i.state='RELEASED') AND EXISTS(SELECT 1 FROM zj_market_b06.b_trade_coordination c WHERE c.order_id=o.order_id AND c.run_state='DONE') AND EXISTS(SELECT 1 FROM group_buy_market_b06.ab_trade_order a WHERE a.out_trade_no=o.order_id AND a.source='b06' AND a.channel='web' AND a.order_status='CANCELLED') AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_trade_work w WHERE w.order_id=o.order_id AND w.state<>'DONE') AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_order_block k WHERE k.order_id=o.order_id AND k.state='ACTIVE' AND k.kind<>'RECONCILIATION')))),'historicalClosedUnpaidReview',(SELECT COUNT(*) FROM zj_market_b06.b_market_order o WHERE o.review_required=1 AND (o.business_status='CLOSED' AND o.last_error IN ('TEAM_FAILED','TEAM_RECONCILIATION_REQUIRED') AND o.close_basis='A_CONFIRMED' AND o.payment_exposure='NEVER_OPENED' AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id) AND EXISTS(SELECT 1 FROM zj_market_b06.b_inventory_reservation i WHERE i.order_id=o.order_id AND i.state='RELEASED') AND EXISTS(SELECT 1 FROM zj_market_b06.b_trade_coordination c WHERE c.order_id=o.order_id AND c.run_state='DONE') AND EXISTS(SELECT 1 FROM group_buy_market_b06.ab_trade_order a WHERE a.out_trade_no=o.order_id AND a.source='b06' AND a.channel='web' AND a.order_status='CANCELLED') AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_trade_work w WHERE w.order_id=o.order_id AND w.state<>'DONE') AND NOT EXISTS(SELECT 1 FROM zj_market_b06.b_order_block k WHERE k.order_id=o.order_id AND k.state='ACTIVE' AND k.kind<>'RECONCILIATION'))),'historicalClosedRefundReview',(SELECT COUNT(*) FROM zj_market_b06.b_market_order o WHERE o.business_status='CLOSED' AND o.review_required=1 AND EXISTS(SELECT 1 FROM zj_market_b06.b_refund r WHERE r.order_id=o.order_id AND r.funds_status='SUCCEEDED' AND r.sync_status='ACCEPTED' AND r.release_status='RELEASED')),'nonReconciliationBlocksActive',(SELECT COUNT(*) FROM zj_market_b06.b_order_block WHERE state='ACTIVE' AND kind<>'RECONCILIATION'),'heldInventory',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_reservation WHERE state='HELD'),'pendingFulfillment',(SELECT COUNT(*) FROM zj_market_b06.b_fulfillment WHERE status='PENDING'),'tradeQuarantineReceipts',(SELECT COUNT(*) FROM zj_market_b06.b_trade_quarantine),'syncQuarantineUnreplayed',(SELECT COUNT(*) FROM zj_market_b06.b_sync_quarantine WHERE replayed_at_ms IS NULL),'aQuarantineReceipts',(SELECT COUNT(*) FROM group_buy_market_b06.ab_quarantine)); COMMIT;")
  return '\n'.join(queries)
 def health(self):
  result={}
  fmt='{"project":"{{index .Config.Labels "com.docker.compose.project"}}","service":"{{index .Config.Labels "com.docker.compose.service"}}","running":{{.State.Running}},"oomKilled":{{.State.OOMKilled}},"health":"{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}","image":"{{.Image}}","restartCount":{{.RestartCount}}}'
  for service in SERVICES:
   try:
    v=json.loads(self.command(self.docker+['inspect','--format',fmt,PROJECT+'-'+service+'-1']))
    if v['project']!=PROJECT or v['service']!=service:raise RuntimeError('OWNERSHIP_MISMATCH')
    v['ok']=v['running'] and v['health']=='healthy' and not v['oomKilled'];result[service]=v
   except Exception:result[service]={'ok':False,'health':'UNKNOWN'}
  try:
   # Gateway's local CA and explicit DNS identity; never -k or disabling revocation.
   out=self.command(self.docker+['exec',PROJECT+'-web-1','curl','--fail','--silent','--show-error','--max-time','5','--cacert','/run/secrets/web-ca.pem','--resolve','zj-market.test:8443:127.0.0.1','https://zj-market.test:8443/healthz'])
   result['https']={'ok':out.strip()=='UP','scope':'strict TLS gateway liveness; not business admission'}
  except Exception:result['https']={'ok':False,'health':'UNKNOWN'}
  return result
 def sample(self):
  start=time.monotonic();snapshot={'at':stamp(),'sampleEpoch':time.time(),'project':PROJECT,'health':self.health(),'databaseStatus':'UNKNOWN','queues':None,'obligations':None,'brokerLag':'NOT_COLLECTED'}
  try:
   self.ownership();rows=self.sql(self.metrics_sql()).splitlines();data=[];cipher=''
   for row in rows:
    if row.startswith('Ssl_cipher\t'):cipher=row.split('\t',1)[1]
    elif row.strip():data.append(json.loads(row))
   if not cipher:raise RuntimeError('DATABASE_TLS_MISSING')
   queues={v['queue']:v for v in data if v['kind']=='queue'}
   if len(queues)!=len(QUEUES):raise RuntimeError('INCOMPLETE_DATABASE_SAMPLE')
   snapshot.update(databaseStatus='OK',databaseNowMs=next(v['databaseNowMs'] for v in data if v['kind']=='clock'),databaseTlsCipher=cipher,queues=queues,obligations=next(v for v in data if v['kind']=='obligations'))
  except Exception as e:snapshot['databaseError']=type(e).__name__ # never driver/SQL/raw payload
  snapshot['durationSeconds']=round(time.monotonic()-start,3)
  snapshot['complete']=snapshot['databaseStatus']=='OK' and all(v['ok'] for v in snapshot['health'].values())
  atomic('latest.json',snapshot);append('samples.jsonl',snapshot);self.alerts(snapshot);return snapshot
 def alerts(self,snapshot):
  pending=load('alerts-pending.json')
  if pending:
   append('alerts.jsonl',pending['event']);atomic('alerts-state.json',pending['state']);(HOME/'alerts-pending.json').unlink()
  before=load('alerts-state.json',{});current=dict(before);conditions={}
  for service,v in snapshot['health'].items():conditions['health:'+service]=(not v['ok'],'CRITICAL')
  conditions['observer:database']=(snapshot['databaseStatus']!='OK','CRITICAL')
  if snapshot['databaseStatus']=='OK':
   for obligation in ('paymentAwaitingA','refundUnfinished'):
    conditions['obligation:'+obligation]=(snapshot['obligations'][obligation]>0 and snapshot['obligations'][obligation+'OldestSeconds']>=300,'WARNING')
   conditions['review:non-reconciliation-block']=(snapshot['obligations']['nonReconciliationBlocksActive']>0,'CRITICAL')
   conditions['review:payment-root']=(snapshot['obligations']['activePaymentReview']>0,'CRITICAL')
   conditions['review:order']=(snapshot['obligations']['activeOrderReview']>0,'CRITICAL')
   for queue,v in snapshot['queues'].items():
    conditions['review:'+queue]=(v['review']>0,'CRITICAL')
    conditions['backlog:'+queue]=(v['due']>0 and v['oldestOverdueSeconds']>=300,'WARNING')
   # Quarantine receipt history is separately reported, not a forever-active task.
  for key,(active,severity) in conditions.items():
   old=before.get(key);was=old is not None and old.get('active',False)
   if active!=was:
    incident=old['incidentId'] if was else secrets.token_hex(12)
    event={'at':snapshot['at'],'event':'alert_firing' if active else 'alert_resolved','key':key,'severity':severity,'incidentId':incident,'project':PROJECT}
    current[key]={'active':active,'incidentId':incident,'changedAt':snapshot['at'],'severity':severity}
    # Durable intent precedes append; replay can repeat the SAME event/incident after a crash.
    atomic('alerts-pending.json',{'event':event,'state':current})
    append('alerts.jsonl',event);atomic('alerts-state.json',current);(HOME/'alerts-pending.json').unlink()
  atomic('alerts-state.json',current)
 def trace(self,kind,identity):
  if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',identity):raise ValueError('INVALID_BUSINESS_ID')
  # Scalar allowlist only; no user, payload, snapshot, request, proof, auth or free-text errors.
  predicates={'order':f"o.order_id='{identity}'",'payment':f"o.order_id IN (SELECT order_id FROM {B}.b_payment WHERE payment_id='{identity}')",'refund':f"o.order_id IN (SELECT order_id FROM {B}.b_refund WHERE refund_id='{identity}')",'team':f"o.order_id IN (SELECT out_trade_no FROM {A}.ab_trade_order WHERE source='b06' AND channel='web' AND team_id='{identity}')",'event':f"o.order_id IN (SELECT order_id FROM {B}.b_trade_outbox WHERE event_id='{identity}')",'task':f"o.order_id IN (SELECT order_id FROM {B}.b_payment WHERE payment_id='{identity}') OR o.order_id IN (SELECT order_id FROM {B}.b_refund WHERE refund_id='{identity}') OR o.order_id IN (SELECT order_id FROM {B}.b_trade_work WHERE work_id='{identity}') OR o.order_id IN (SELECT local_order_id FROM {B}.b_reconciliation_member WHERE task_id='{identity}')"}
  # Reconciliation member added to grants below; identifiers bind through validated ASCII only.
  sql=f"""SET SESSION time_zone='+00:00'; SET SESSION max_execution_time=5000; START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;
SELECT JSON_OBJECT('event','business_trace','orderId',o.order_id,'orderStatus',o.business_status,'reviewRetained',o.review_required,'paymentId',p.payment_id,'funds',p.funds_state,'amount',p.amount,'aPayment',p.a_acceptance,'paidAtMs',p.paid_at_ms,'refundId',r.refund_id,'refundAmount',r.amount,'refundFunds',r.funds_status,'refundSync',r.sync_status,'inventoryRelease',r.release_status,'teamId',ao.team_id,'aTeamStatus',at.team_status,'aPaidCount',at.paid_count,'aReservedCount',at.reserved_count,'aRefundStatus',ao.refund_status,'reservation',ir.state,'stockAvailable',ia.available,'stockReserved',ia.reserved,'stockSold',ia.sold,'confirmLedgers',(SELECT COUNT(*) FROM {B}.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='CONFIRM'),'releaseLedgers',(SELECT COUNT(*) FROM {B}.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='RELEASE'),'work',(SELECT COALESCE(JSON_ARRAYAGG(JSON_OBJECT('taskId',w.work_id,'kind',w.kind,'state',w.state)),JSON_ARRAY()) FROM {B}.b_trade_work w WHERE w.order_id=o.order_id),'events',(SELECT COALESCE(JSON_ARRAYAGG(JSON_OBJECT('eventId',e.event_id,'state',e.state)),JSON_ARRAY()) FROM {B}.b_trade_outbox e WHERE e.order_id=o.order_id))
FROM {B}.b_market_order o LEFT JOIN {B}.b_payment p ON p.order_id=o.order_id LEFT JOIN {B}.b_refund r ON r.order_id=o.order_id LEFT JOIN {A}.ab_trade_order ao ON ao.out_trade_no=o.order_id AND ao.source='b06' AND ao.channel='web' LEFT JOIN {A}.ab_team at ON at.team_id=ao.team_id LEFT JOIN {B}.b_inventory_reservation ir ON ir.order_id=o.order_id LEFT JOIN {B}.b_inventory_account ia ON ia.goods_id=o.goods_id WHERE {predicates[kind]} ORDER BY o.order_id LIMIT 101; COMMIT;"""
  rows=[json.loads(v) for v in self.sql(sql).splitlines() if v.strip()]
  if len(rows)>100:raise RuntimeError('TRACE_TOO_LARGE_NARROW_QUERY')
  result={'at':stamp(),'kind':kind,'identity':identity,'rows':rows};atomic('last-trace.json',result);append('traces.jsonl',result);return result

TABLES[B].add('b_reconciliation_member')
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['init','once','watch','status','trace']);p.add_argument('--context',default='desktop-linux');p.add_argument('--interval',type=int,default=30);p.add_argument('--kind',choices=['order','payment','refund','team','event','task']);p.add_argument('--id');a=p.parse_args()
 HOME.mkdir(parents=True,exist_ok=True)
 if a.action=='status':
  s=load('latest.json');age=None if s is None else time.time()-s['sampleEpoch'];fresh=age is not None and 0<=age<=90
  active={k:v for k,v in load('alerts-state.json',{}).items() if v['active']};ok=fresh and bool(s['complete']) and not active if s else False
  print(json.dumps({'ok':ok,'fresh':fresh,'ageSeconds':age,'complete':fresh and s['complete'] if s else False,'activeAlerts':active,'scope':'local files; watch must be running; stale is UNKNOWN'},ensure_ascii=False));return 0 if ok else 2
 with exclusive():
  o=Observer(a.context)
  if a.action=='init':
   module('materials',ROOT/'scripts/prepare-b06-secrets.py').protect_windows(HOME);o.setup();print('Observer SELECT-only principal ready');return 0
  if a.action=='trace':
   if not a.kind or not a.id:p.error('trace requires --kind and --id')
   print(json.dumps(o.trace(a.kind,a.id),ensure_ascii=False));return 0
  if not 10<=a.interval<=60:p.error('interval must be 10..60 seconds')
  while True:
   s=o.sample();print(json.dumps({'at':s['at'],'complete':s['complete'],'database':s['databaseStatus'],'privateSnapshot':str(HOME/'latest.json')}),flush=True)
   if a.action=='once':return 0 if s['complete'] else 2
   time.sleep(a.interval)
if __name__=='__main__':
 try:raise SystemExit(main())
 except KeyboardInterrupt:print('Observer stopped; recovery services continue')
 except Exception as e:print('Observer failed: '+type(e).__name__);raise SystemExit(2)
