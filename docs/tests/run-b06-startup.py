"""B06.2 real Docker initialization, restart, schema/admission and recovery acceptance.
Uses the owned main deployment plus one fresh, isolated batch. Never removes volumes.
"""
from pathlib import Path
import argparse,importlib.util,json,subprocess,time,hashlib,os
ROOT=Path(__file__).resolve().parents[2]
def module(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/'scripts/b06-deployment.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main(name,context):
 import re
 if not re.fullmatch('b062-[a-z0-9-]+',name):raise ValueError('Fresh B062 name required')
 work=ROOT/'.local/b06/acceptance'/name
 if work.exists():raise ValueError('Never overwrite acceptance evidence')
 work.mkdir(parents=True)
 m=module('main_deployment');d=m.Deployment(context)
 report={'runName':name,'status':'RUNNING','checks':[],'scope':'Windows Docker; real complete schemas and services; no third-party funds or browser UI acceptance'}
 def check(label,operation):
  result=operation();report['checks'].append({'name':label,'status':'PASSED'});(work/'progress.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS '+label,flush=True);return result
 def snapshot():
  sql="SELECT 'users',COUNT(*) FROM zj_market_b06.b_user UNION ALL SELECT 'products',COUNT(*) FROM zj_market_b06.b_product UNION ALL SELECT 'ledger',COUNT(*) FROM zj_market_b06.b_inventory_ledger UNION ALL SELECT 'discounts',COUNT(*) FROM group_buy_market_b06.group_buy_discount UNION ALL SELECT 'activities',COUNT(*) FROM group_buy_market_b06.group_buy_activity UNION ALL SELECT 'mappings',COUNT(*) FROM group_buy_market_b06.sc_sku_activity; SELECT activity_id,discount_id,start_time,end_time FROM group_buy_market_b06.group_buy_activity ORDER BY activity_id; SELECT goods_id,available,reserved,sold,inventory_version FROM zj_market_b06.b_inventory_account ORDER BY goods_id;"
  return d.admin('seed-snapshot',sql)
 def unchanged(a,b):
  if a!=b:raise AssertionError('Snapshot changed')
 def client(mode):return d.run('client-'+mode,['node',ROOT/'docs/tests/b06-startup-client.mjs',mode],expected='CLIENT_PASS')
 def resources(label):
  ids=d.run(label+'-ids',d.docker+['ps','--filter','label=com.docker.compose.project='+m.PROJECT,'--format','{{.ID}}']).splitlines()
  rows=json.loads(d.run(label+'-inspect',d.docker+['inspect']+ids));states=[{'name':r['Name'],'image':r['Image'],'oomKilled':r['State']['OOMKilled'],'restarts':r['RestartCount'],'health':r['State'].get('Health',{}).get('Status'),'memoryLimit':r['HostConfig']['Memory']} for r in rows]
  assert len(states)==7 and all(x['health']=='healthy' and not x['oomKilled'] for x in states)
  (work/(label+'-containers.json')).write_text(json.dumps(states,indent=2)+'\n')
  stats=d.run(label+'-usage',d.docker+['stats','--no-stream','--format','{{json .}}']+[r['Id'] for r in rows]);(work/(label+'-usage.jsonl')).write_text(stats)
  return states
 shared=[n for n in d.run('all-original-containers',d.docker+['ps','-a','--format','{{.Names}}']).splitlines() if not n.startswith('zj-market-')]
 projection='{"Id":"{{.Id}}","Name":"{{.Name}}","Image":"{{.Image}}","State":{"Running":{{.State.Running}}}}'
 before_shared=[json.loads(line) for line in d.run('shared-before',d.docker+['inspect','--format',projection]+shared).splitlines()]
 shared_identity=lambda rows:{r['Name']:{'id':r['Id'],'running':r['State']['Running'],'image':r['Image']} for r in rows}
 before_git=subprocess.check_output(['git','status','--porcelain'],cwd='D:/Java/group-buy-market',text=True)
 fresh=None;main_stopped=False
 try:
  check('main-schema-runtime-boundaries-tls-locked-migrators',d.ready)
  money=d.admin('prelude-requires-no-financial-fixtures',"SELECT COUNT(*) FROM zj_market_b06.b_payment; SELECT COUNT(*) FROM zj_market_b06.b_refund;")
  assert money.splitlines()==['0','0'],'Use an untransacted B062 demonstration environment'
  initial_snapshot=snapshot()
  before_releases=int(d.admin('release-count-before',"SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger WHERE kind='RELEASE';").strip())
  check('controlled-open-before-new-recovery-order',lambda:d.start('open'))
  check('new-unpaid-order-real-a-reservation',lambda:client('hold'))
  check('maintenance-reloads-b-before-backend-check',lambda:d.start('maintenance'))
  check('backend-checkout-disabled-even-bypassing-gateway',lambda:client('checkout-gate'))
  assert d.admin('backend-rejection-created-no-payment',"SELECT COUNT(*) FROM zj_market_b06.b_payment;").strip()=='0'
  check('reopen-reloads-b-after-backend-negative',lambda:d.start('open'))
  check('only-owned-a-paused-for-durable-close-proof',lambda:d.run('pause-owned-a',d.compose+['stop','marketing-a']))
  check('cancel-accepted-while-a-unavailable',lambda:client('cancel'))
  order=json.loads((m.CONTROL/'smoke-order.json').read_text())['orderId']
  pending=d.admin('persisted-close-before-maintenance',"SELECT business_status,payment_exposure FROM zj_market_b06.b_market_order WHERE order_id='"+order+"';")
  assert pending.strip()=='CLOSING\\tNEVER_OPENED'.replace('\\t','\t');(work/'pending-close-before-maintenance.txt').write_text(pending)
  check('pending-close-durable-before-restart',lambda:True)
  check('maintenance-restores-old-tasks-with-checkout-off',lambda:d.start('maintenance'))
  check('maintenance-gateway-default-deny-and-cancel-auth',lambda:client('gateway'))
  check('persisted-unpaid-close-recovered-with-checkout-off',lambda:client('closed'))
  balance=d.admin('recovered-stock-and-money-empty',"SELECT available,reserved,sold FROM zj_market_b06.b_inventory_account; SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger WHERE kind='RELEASE'; SELECT COUNT(*) FROM zj_market_b06.b_payment; SELECT COUNT(*) FROM zj_market_b06.b_refund;")
  assert balance.splitlines()==['100\t0\t0',str(before_releases+1),'0','0'];(work/'recovery-balances.txt').write_text(balance)
  check('inventory-release-once-no-synthetic-payment-refund',lambda:True)
  check('main-all-seven-services-healthy-resource-sample',lambda:resources('before-restart'))
  before=snapshot()
  check('repeat-init-no-data-reset',d.initialize)
  check('repeat-init-preserves-seeds-stock-and-activity-deadline',lambda:unchanged(before,snapshot()))
  # Explicit repeat migration (accounts locked again even on verification failure).
  d.admin('unlock-for-explicit-replay',"ALTER USER 'a_migrator'@'%' ACCOUNT UNLOCK; ALTER USER 'b_migrator'@'%' ACCOUNT UNLOCK;")
  try:
   check('a-journal-replay-preserves-applied-ddl',lambda:d.tool('a-init'))
   result=check('flyway-validate-replay-zero-migration',lambda:d.tool('migrate'));assert 'No migration necessary' in result
   check('transactional-seed-replay-original-ids-and-stock-operation',lambda:d.tool('seed'));d.seed_a((m.CONTROL/'seed-goods-id.txt').read_text().strip())
  finally:d.admin('lock-after-explicit-replay',"ALTER USER 'a_migrator'@'%' ACCOUNT LOCK; ALTER USER 'b_migrator'@'%' ACCOUNT LOCK;")
  check('all-replays-preserve-seeds-stock-and-activity-deadline',lambda:unchanged(before,snapshot()))
  # Startup must close the public gate before detecting schema mismatch.
  d.admin('controlled-schema-drift',"ALTER TABLE zj_market_b06.b_database_probe ADD COLUMN b06_schema_drift_test INT NULL;")
  try:
   rejected=False
   try:d.start('open')
   except RuntimeError as e:rejected='Schema drift' in str(e)
   assert rejected and d.state()['mode']=='maintenance'
   check('schema-drift-refuses-open-and-keeps-gateway-closed',lambda:client('gateway'))
  finally:d.admin('restore-exact-schema',"ALTER TABLE zj_market_b06.b_database_probe DROP COLUMN b06_schema_drift_test;")
  check('restored-original-schema-no-baseline-rewrite',d.ready)
  d.admin('controlled-constraint-drift',"ALTER TABLE zj_market_b06.b_database_probe ADD CONSTRAINT b06_drift_check CHECK (LENGTH(probe_value)>=0);")
  try:
   rejected=False
   try:d.ready()
   except RuntimeError as e:rejected='Schema drift' in str(e)
   assert rejected;check('constraint-drift-also-refuses-readiness',lambda:True)
  finally:d.admin('restore-exact-constraints',"ALTER TABLE zj_market_b06.b_database_probe DROP CHECK b06_drift_check;")
  check('restored-full-schema-and-migration-history',d.ready)
  # Real process lock test: a second CLI fails before accessing Docker/DB.
  with (m.CONTROL/'command.lock').open('r+b') as lock:
   if os.name=='nt':
    import msvcrt
    msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
   else:
    import fcntl
    fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
   process=subprocess.run([__import__('sys').executable,'-B',str(ROOT/'scripts/b06-deployment.py'),'ready','--context',context],capture_output=True,text=True)
   assert process.returncode!=0 and 'PASS mysql-identity' not in process.stdout
   (work/'concurrent-command-rejection.txt').write_text(process.stdout+process.stderr)
  check('concurrent-deployment-command-rejected',lambda:True)
  check('owned-main-controlled-stop-retains-volumes',d.stop);main_stopped=True
  # A truly empty second environment proves corrected inputs, not adoption of earlier partial DDL.
  fm=module('fresh_deployment');fm.PROJECT='zj-market-'+name;fm.CONTROL=work/'fresh-control';fm.RUNTIME=work/'fresh-runtime';fm.BUILD=work/'fresh-build';fm.BUILD.mkdir()
  d.run('fresh-private-materials',[__import__('sys').executable,'-B',ROOT/'scripts/prepare-b06-secrets.py','--directory',fm.RUNTIME,'--java-home','C:/Program Files/Java/jdk-21'])
  env=(m.BUILD/'release.env').read_text();env=re.sub(r'^B06_SECRET_DIR=.*$', 'B06_SECRET_DIR='+fm.RUNTIME.as_posix(),env,flags=re.M);(fm.BUILD/'release.env').write_text(env)
  fresh=fm.Deployment(context)
  check('fresh-empty-volumes-explicit-a-ddl-b-v18-48-grants-seed-topics',fresh.initialize)
  check('fresh-complete-maintenance-start-real-sync-and-signed-trial',lambda:fresh.start('maintenance'))
  counts=fresh.admin('fresh-no-old-business',"SELECT COUNT(*) FROM zj_market_b06.b_user; SELECT COUNT(*) FROM zj_market_b06.b_product; SELECT available,reserved,sold FROM zj_market_b06.b_inventory_account; SELECT COUNT(*) FROM zj_market_b06.b_market_order; SELECT COUNT(*) FROM zj_market_b06.b_payment; SELECT COUNT(*) FROM zj_market_b06.b_refund; SELECT COUNT(*) FROM group_buy_market_b06.ab_trade_order;")
  assert counts.splitlines()==['3','1','100\t0\t0','0','0','0','0'];(work/'fresh-counts.txt').write_text(counts)
  check('fresh-has-only-new-demo-seeds-no-orders-or-money-facts',lambda:True)
  check('fresh-init-repeat-safe',fresh.initialize)
  fresh.stop();fresh.run('fresh-cleanup-containers-networks-only',fresh.compose+['down','--remove-orphans']);fresh=None
  check('main-cold-restart-original-volumes-readiness-then-open',lambda:d.start('open'));main_stopped=False
  check('cold-restart-preserves-original-seeds-stock-and-deadline',lambda:unchanged(before,snapshot()))
  check('final-actual-a-b-sync-rpc-identity-https-ready',lambda:client('ready'))
  check('final-all-seven-services-healthy-no-oom-resource-sample',lambda:resources('after-restart'))
  after_shared=[json.loads(line) for line in d.run('shared-after',d.docker+['inspect','--format',projection]+shared).splitlines()];assert shared_identity(before_shared)==shared_identity(after_shared)
  assert before_git==subprocess.check_output(['git','status','--porcelain'],cwd='D:/Java/group-buy-market',text=True)
  check('shared-containers-and-external-a-worktree-preserved',lambda:True)
  report['status']='PASSED';report['finalMode']=d.state()['mode'];report['mainState']=d.state();report['recoveryOrder']=json.loads((m.CONTROL/'smoke-order.json').read_text());report['sharedContainers']=shared_identity(after_shared)
 except Exception as e:report['status']='FAILED';report['error']=str(e);raise
 finally:
  if fresh is not None:
   try:fresh.run('failed-fresh-container-diagnostics',fresh.compose+['logs','--no-color','--tail','100']);fresh.run('failed-fresh-cleanup-only',fresh.compose+['down','--remove-orphans'])
   except Exception as e:report['cleanupError']=str(e)
  if main_stopped:
   try:d.start('maintenance');report['mainRestoredToMaintenance']=True
   except Exception as e:report['mainRestoreError']=str(e)
  (work/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print('B062_STARTUP_'+report['status'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);p.add_argument('--context',default='desktop-linux');a=p.parse_args();main(a.run_name,a.context)
