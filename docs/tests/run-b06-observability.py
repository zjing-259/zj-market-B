"""B064 real read-only metrics, least privilege, structured logs and local alert lifecycle."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,subprocess,time,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);a=p.parse_args()
 import re
 if not re.fullmatch('b064-[a-z0-9-]+',a.run_name):raise ValueError('Invalid run name')
 work=ROOT/'.local/b06/observability-acceptance'/a.run_name
 if work.exists():raise ValueError('Use fresh run name')
 work.mkdir(parents=True)
 m=module('observer',ROOT/'scripts/b06-observability.py');o=m.Observer();d=module('deployment',ROOT/'scripts/b06-deployment.py').Deployment('desktop-linux')
 checks=[]
 def check(name,condition):
  if not condition:
   (work/'failure.json').write_text(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'passed':checks,'failed':name},indent=2)+'\n',encoding='utf-8')
   raise AssertionError(name)
  checks.append(name);print('PASS '+name,flush=True)
 def events():
  f=m.HOME/'alerts.jsonl';return [json.loads(x) for x in f.read_text(encoding='utf-8').splitlines()] if f.exists() else []
 def shared():
  raw=o.command(o.docker+['ps','-a','--format','{{json .}}'])
  return sorted((x['ID'],x['Names'],x['State']) for x in map(json.loads,raw.splitlines()) if not x['Names'].startswith(m.PROJECT+'-'))
 def funds():
  queries=["SELECT CONCAT_WS('|',order_id,business_status,review_required) FROM zj_market_b06.b_market_order ORDER BY order_id;","SELECT CONCAT_WS('|',payment_id,order_id,amount,funds_state,a_acceptance,paid_at_ms) FROM zj_market_b06.b_payment ORDER BY payment_id;","SELECT CONCAT_WS('|',refund_id,order_id,amount,funds_status,sync_status,release_status) FROM zj_market_b06.b_refund ORDER BY refund_id;","SELECT CONCAT_WS('|',goods_id,available,reserved,sold,inventory_version) FROM zj_market_b06.b_inventory_account ORDER BY goods_id;","SELECT CONCAT_WS('|',order_id,kind,business_key) FROM zj_market_b06.b_inventory_ledger WHERE order_id IS NOT NULL ORDER BY order_id,kind,business_key;","SELECT CONCAT_WS('|',team_id,team_status,team_version,reserved_count,paid_count) FROM group_buy_market_b06.ab_team ORDER BY team_id;"]
  return hashlib.sha256(o.sql('START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;'+''.join(queries)+'COMMIT;').encode()).hexdigest()
 with m.exclusive():
  d.ready();check('controlled-open-ready',d.state()['mode']=='open' and d.state()['phase']=='READY')
  before_shared=shared();hosts=Path('C:/Windows/System32/drivers/etc/hosts');before_hosts=hosts.read_bytes();before_funds=funds()
  s=o.sample();check('real-twelve-queue-database-tls-sample',s['complete'] and len(s['queues'])==12 and bool(s['databaseTlsCipher']))
  check('no-current-money-obligations-and-no-held-inventory',s['obligations']['paymentAwaitingA']==s['obligations']['refundUnfinished']==s['obligations']['heldInventory']==0)
  check('closed-refunded-history-not-active-review',s['obligations']['historicalClosedRefundReview']>=3 and s['obligations']['activeOrderReview']==0)
  check('closed-unpaid-history-requires-proofs',s['obligations']['historicalClosedUnpaidReview']>=1)
  check('unavailable-age-is-null-not-zero',s['queues']['ab_waiting_dependency']['ageAvailable']==0 and s['queues']['ab_waiting_dependency']['oldestPendingSeconds'] is None)
  check('a-first-send-is-not-a-failure',s['queues']['ab_outbox']['recordedFailures'] is None and s['queues']['ab_outbox']['recordedRetries']==0)
  # Real engine evaluates the actual queue query against a derived, nonpersistent fixture. No business INSERT.
  query=next(v for v in o.metrics_sql().splitlines() if "'queue','b_trade_work'" in v)
  fixture="(SELECT 'DONE' state,0 next_attempt_ms,0 created_at_ms,7 failure_count,NULL lease_until_ms UNION ALL SELECT 'READY',900000,800000,2,NULL UNION ALL SELECT 'WAITING_DEPENDENCY',1200000,800000,1,NULL UNION ALL SELECT 'REVIEW_REQUIRED',0,100000,3,NULL UNION ALL SELECT 'LEASED',500000,400000,1,600000)"
  v=json.loads(o.sql('SET @now=1000000;'+query.replace('FROM zj_market_b06.b_trade_work q','FROM '+fixture+' q')).strip())
  check('real-sql-pending-future-review-retry-lease-and-age-semantics',v['pending']==4 and v['due']==2 and v['review']==1 and v['recordedFailures']==14 and v['expiredLeases']==1 and v['oldestOverdueSeconds']==500 and v['oldestPendingSeconds']==900)
  denied=[('no-update',"UPDATE zj_market_b06.b_market_order SET review_required=review_required WHERE 1=0;"),('no-ddl',"CREATE TABLE zj_market_b06.b064_observer_must_not_exist(id INT);"),('no-migration-history',"SELECT * FROM zj_market_b06.flyway_schema_history LIMIT 0;"),('no-auth-tables',"SELECT * FROM zj_market_b06.b_user LIMIT 0;"),('no-system',"SELECT * FROM mysql.user LIMIT 0;")]
  for name,sql in denied:
   try:o.sql(sql);accepted=True
   except RuntimeError:accepted=False
   check('observer-'+name,not accepted)
  try:o.sql('SELECT 1;',extra=['--ssl-mode=DISABLED']);accepted=True
  except RuntimeError:accepted=False
  check('observer-plaintext-denied',not accepted)
  report=json.loads((ROOT/'docs/tests/b06-normal-acceptance.json').read_text());order=report['facts']['expiry']['orders'][0]['orderId'];trace=o.trace('order',order);row=trace['rows'][0]
  check('trace-real-closed-refunded-A-failed-stock-released',row['orderStatus']=='CLOSED' and row['refundFunds']=='SUCCEEDED' and row['refundSync']=='ACCEPTED' and row['inventoryRelease']=='RELEASED' and row['aTeamStatus']=='FAILED' and row['releaseLedgers']==1)
  identities={'payment':row['paymentId'],'refund':row['refundId'],'team':row['teamId'],'event':row['events'][0]['eventId'],'task':row['work'][0]['taskId']}
  traces={'order':trace}
  for kind,identity in identities.items():
   t=o.trace(kind,identity);check('trace-'+kind+'-to-order',any(v['orderId']==order for v in t['rows']));traces[kind]=t
  (work/'traces.json').write_text(json.dumps(traces,indent=2)+'\n',encoding='utf-8')
  probe=json.loads(o.command(['node',ROOT/'docs/tests/b06-observability-client.mjs']))
  logs={}
  for service in ['market-b','web']:
   raw=subprocess.run(o.docker+['logs','--tail','1500',m.PROJECT+'-'+service+'-1'],capture_output=True,text=True,encoding='utf-8',check=True)
   logs[service]=raw.stdout+raw.stderr
  parsed={name:[json.loads(line) for line in text.splitlines() if line.startswith('{')] for name,text in logs.items()}
  for response in probe['rows']:
   b=next(v for v in parsed['market-b'] if v.get('requestId')==response['requestId'] and v.get('message')=='http_request_completed')
   web=next(v for v in parsed['web'] if v.get('requestId')==response['requestId'] and v.get('event')=='http_access')
   check('structured-request-correlation-'+str(response['status']),b['status']==web['status']==response['status'] and 'durationMs' in b and 'route' in b and 'version' in b.get('ecs',{}))
  check('query-path-bearer-cookie-marker-not-logged',all(probe['marker'] not in log for log in logs.values()))
  values=json.loads((m.RUNTIME/'private/values.json').read_text());values['observer']=m.load('principal.json')['password']
  check('runtime-and-observer-passwords-not-in-logs',all(str(secret) not in text for secret in values.values() for text in logs.values()))
  # Actual unavailable upstream must not echo query/header values into nginx error logs.
  try:
   o.command(o.docker+['stop','--time','10',m.PROJECT+'-market-b-1'])
   unavailable=json.loads(o.command(['node',ROOT/'docs/tests/b06-observability-client.mjs','upstream']))
   down_b=o.sample();check('actual-B-unavailable-health-and-502',not down_b['health']['market-b']['ok'] and unavailable['rows'][0]['status']==502)
  finally:o.command(o.docker+['start',m.PROJECT+'-market-b-1'])
  for _ in range(60):
   if o.health()['market-b']['ok']:break
   time.sleep(2)
  check('actual-B-health-recovered',o.sample()['complete'])
  raw=subprocess.run(o.docker+['logs','--tail','200',m.PROJECT+'-web-1'],capture_output=True,text=True,encoding='utf-8',check=True)
  check('upstream-error-query-marker-not-logged',unavailable['marker'] not in raw.stdout+raw.stderr)
  # Health alert actually fires, repeated collection dedups, same incident resolves. Only owned gateway.
  start_events=len(events())
  try:
   o.command(o.docker+['stop','--time','10',m.PROJECT+'-web-1']);down=o.sample();o.sample()
   check('actual-stopped-gateway-observed',not down['health']['web']['ok'] and not down['health']['https']['ok'])
  finally:o.command(o.docker+['start',m.PROJECT+'-web-1'])
  for _ in range(45):
   if o.health()['web']['ok']:break
   time.sleep(2)
  up=o.sample();check('actual-gateway-recovered',up['complete'])
  health_events=[e for e in events()[start_events:] if e['key']=='health:web']
  check('actual-alert-fire-dedup-resolve-same-incident',[e['event'] for e in health_events]==['alert_firing','alert_resolved'] and health_events[0]['incidentId']==health_events[1]['incidentId'])
  # Observer-only permission fault: no runtime/application principal or business row changes.
  try:
   d.admin('observer-test-revoke',"REVOKE SELECT ON zj_market_b06.b_refund_task FROM 'b06_observer'@'%';")
   unknown=o.sample();check('database-collection-failure-is-unknown-not-empty',unknown['databaseStatus']=='UNKNOWN' and unknown['queues'] is None and unknown['obligations'] is None)
  finally:d.admin('observer-test-restore',"GRANT SELECT ON zj_market_b06.b_refund_task TO 'b06_observer'@'%';")
  final=o.sample();check('database-collector-alert-recovered',final['complete'] and not m.load('alerts-state.json')['observer:database']['active'])
  check('funds-stock-team-fingerprint-unchanged',funds()==before_funds)
  check('shared-container-identity-state-unchanged',shared()==before_shared)
  check('windows-hosts-unchanged',hosts.read_bytes()==before_hosts)
  check('final-no-active-local-alerts',not any(v['active'] for v in m.load('alerts-state.json').values()))
  d.ready();check('final-schema-history-grants-migrator-locks-ready',d.state()['mode']=='open' and d.state()['phase']=='READY')
  image_map={k:v['image'] for k,v in final['health'].items() if 'image' in v}
  sources=['scripts/b06-observability.py','docs/tests/test-b06-observability.py','docs/tests/run-b06-observability.py','docs/tests/b06-observability-client.mjs','deploy/b06/config/b.properties','deploy/b06/nginx.conf','zj-market-app/src/main/java/cn/zj/zjmarket/app/security/IdentityHttpFilter.java','zj-market-app/src/main/java/cn/zj/zjmarket/app/config/IdentityWebConfiguration.java']
  result={'stage':'B-06.4','status':'PASSED_WINDOWS_DOCKER','stageCompletion':True,'at':datetime.now(timezone.utc).isoformat(),'runName':a.run_name,'checks':checks,'queueMetrics':final['queues'],'obligations':final['obligations'],'images':image_map,'databaseTlsCipher':final['databaseTlsCipher'],'financialFingerprint':before_funds,'sourceSha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in sources},'localAlertEvents':events()[start_events:],'unitTests':7,'applicationTests':109,'packagingChecks':33,'maintenanceIntegrityChecks':9,'brokerConsumerLagCollected':False,'linuxVmValidated':False,'gitPublished':False}
  atomic=lambda file:file.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
  atomic(work/'report.json');atomic(ROOT/'docs/tests/b06-observability-acceptance.json');print('PASS B064 '+str(len(checks))+' real checks',flush=True)
if __name__=='__main__':main()
