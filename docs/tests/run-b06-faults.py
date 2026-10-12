"""Real, bounded B065 Windows Docker fault matrix. Business writes use actual APIs/domain methods."""
from pathlib import Path
import hashlib,json,time
ROOT=Path(__file__).resolve().parents[2]
def run(f):
 from datetime import datetime,timezone
 def shared():return f.docker('shared-state',['ps','-a','--filter','label=com.docker.compose.project!=zj-market-b06','--format','{{.ID}} {{.Names}} {{.Image}} {{.State}}']).stdout
 hosts=Path('C:/Windows/System32/drivers/etc/hosts');hosthash=hashlib.sha256(hosts.read_bytes()).hexdigest();others=shared();baseline={s:f.inspect(s) for s in ('mysql','redis','namesrv','broker','marketing-a','market-b','web')};f.report['baseline']={s:{k:v[k] for k in ('id','image','restart','command')} for s,v in baseline.items()};f.save()
 oldids=f.query('SELECT order_id FROM zj_market_b06.b_market_order ORDER BY order_id;').splitlines();oldlist=','.join("'"+x+"'" for x in oldids) or "''"
 oldsql=f"SELECT order_id,payment_id,amount,funds_state,a_acceptance,success_hash,paid_at_ms FROM zj_market_b06.b_payment WHERE order_id IN ({oldlist}) ORDER BY order_id; SELECT order_id,refund_id,amount,funds_status,sync_status,release_status,success_hash FROM zj_market_b06.b_refund WHERE order_id IN ({oldlist}) ORDER BY order_id,refund_id; SELECT order_id,kind,goods_id,delta_available FROM zj_market_b06.b_inventory_ledger WHERE order_id IN ({oldlist}) ORDER BY order_id,kind;"
 oldhash=hashlib.sha256(f.query(oldsql).encode()).hexdigest();f.report['oldFacts']={'orderCount':len(oldids),'sha256':oldhash};f.save();f.sample('baseline')
 # Safe read-only transport positive before any business fixture.
 f.transport();f.transport('signed',True)
 f.client('prepare');fp=f.work/'fixture.json';fixture=f.fixture();fixture['activities']={}
 base=int(f.query('SELECT GREATEST(650000,COALESCE(MAX(activity_id),0))+1 FROM group_buy_market_b06.group_buy_activity;'))
 for i,(name,goods) in enumerate(fixture['goods'].items()):
  activity=base+i;discount=activity*100+1;minutes=2 if name.startswith('refund') else 30
  f.query(f"USE group_buy_market_b06; START TRANSACTION; INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) VALUES ('{discount}','B065 {name}','Ten yuan reduction',0,'ZJ','10'); INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time) VALUES ({activity},'B065 {name}','{discount}',1,10,2,{minutes},1,UTC_TIMESTAMP()-INTERVAL 1 HOUR,UTC_TIMESTAMP()+INTERVAL 30 DAY); INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES ('b06','web',{activity},'{goods}'); COMMIT;")
  fixture['activities'][name]={'activityId':activity,'discountId':discount,'validMinutes':minutes}
 from importlib.util import spec_from_file_location,module_from_spec
 # Atomic fixture save; future HTTP writes keep stable keys in this same file.
 tmp=fp.with_suffix('.tmp');tmp.write_text(json.dumps(fixture,indent=2));tmp.replace(fp)
 f.event('fresh-fixtures-created',goods=fixture['goods'])
 f.client('hold','aClose','unpaid')
 with f.down('marketing-a',kill=True):
  r=f.client('unavailable','aClose');f.check('A-down-new-payment-not-accepted',not r.get('accepted',False),r);f.check('A-down-no-payment-root',f.order('aClose')['payments']==0)
  f.client('cancel','aClose');v=f.order('aClose');f.check('A-down-close-keeps-stock',v['status']=='CLOSING' and v['released']==0 and v['reservation']=='HELD',v)
  f.check('A-down-independent-catalog',f.client('probe','/products')['code']=='0000');f.sample('A-killed')
 f.closed('aClose')
 f.client('hold','first','success');f.client('create','first','lose');oid=f.oid('first')
 identitysql=f"SELECT payment_id,attempt_id,operation_id,request_hash FROM zj_market_b06.b_payment_operation WHERE payment_id IN (SELECT payment_id FROM zj_market_b06.b_payment WHERE order_id='{oid}') ORDER BY operation_id;"
 # Payment operation has receipt IDs, not an independent attempt FK; use canonical attempt table below.
 identitysql=f"SELECT p.payment_id,a.attempt_id,a.request_hash FROM zj_market_b06.b_payment p JOIN zj_market_b06.b_payment_attempt a ON a.payment_id=p.payment_id WHERE p.order_id='{oid}' ORDER BY a.attempt_id;"
 accepted=f.query(identitysql);f.check('lost-receipt-persisted-one-attempt',len(accepted.splitlines())==1)
 with f.down('market-b',kill=True):f.sample('B-killed')
 r=f.client('replay-create','first');f.check('lost-receipt-replay-same-attempt',f.query(identitysql)==accepted,r)
 factsql=f"SELECT p.payment_id,p.amount,p.paid_at_ms,p.success_hash,sa.attempt_id,sa.request_hash,sa.paid_at_ms FROM zj_market_b06.b_payment p JOIN zj_market_b06.b_sim_attempt sa ON sa.payment_id=p.payment_id WHERE p.order_id='{oid}' AND sa.state='SUCCEEDED';"
 outsql=f"SELECT event_id,body_hash FROM zj_market_b06.b_trade_outbox WHERE order_id='{oid}' ORDER BY event_id;"
 with f.down('broker'):
  f.client('choose','first');v=f.order('first');f.check('broker-down-local-payment-kept',v['successful']==1 and v['accepted']==0 and v['released']==v['confirmed']==v['fulfillments']==0 and v['reservation']=='HELD',v)
  paid=f.query(factsql);events=f.query(outsql);f.check('broker-down-durable-outbox',bool(events));f.sample('broker-stopped')
  with f.down('market-b',kill=True):pass
  f.check('broker-down-B-restart-keeps-payment-and-event',f.query(factsql)==paid and f.query(outsql)==events);f.sample('B-recovered-broker-down')
 f.wait('first-A-accepted',lambda:f.order('first'),lambda v:v['accepted']==1)
 team=f.fixture()['orders']['first']['teamId'];f.client('hold','second','success','b06buyer2',team);f.client('create','second')
 with f.down('namesrv'):
  f.transport(expect_fail=True);f.client('choose','second');f.check('namesrv-down-known-channel-fact-kept',f.order('second')['successful']==1);f.sample('namesrv-stopped')
 f.transport()
 for name in ('first','second'):f.wait('completed-once-'+name,lambda n=name:f.order(n),lambda v:v['status']=='GROUP_COMPLETED' and v['confirmed']==v['fulfillments']==1 and v['released']==0)
 f.check('original-paid-fact-and-outbox-unchanged',f.query(factsql)==paid and f.query(outsql)==events)
 moneyhash=hashlib.sha256(f.query("SELECT payment_id,amount,funds_state,success_hash,paid_at_ms FROM zj_market_b06.b_payment ORDER BY payment_id; SELECT order_id,kind,goods_id,delta_available FROM zj_market_b06.b_inventory_ledger ORDER BY order_id,kind;").encode()).hexdigest()
 with f.down('mysql'):
  r=f.client('probe','/products');f.check('database-down-public-read-fails-closed',r.get('code')!='0000',r);v=f.sample('mysql-stopped');f.check('database-down-observation-is-unknown',v['databaseStatus']=='UNKNOWN' and v['queues'] is None and v['obligations'] is None)
 f.wait('database-pools-recovered',lambda:f.client('probe','/products'),lambda v:v.get('code')=='0000')
 f.check('database-restart-keeps-money-and-ledgers',hashlib.sha256(f.query("SELECT payment_id,amount,funds_state,success_hash,paid_at_ms FROM zj_market_b06.b_payment ORDER BY payment_id; SELECT order_id,kind,goods_id,delta_available FROM zj_market_b06.b_inventory_ledger ORDER BY order_id,kind;").encode()).hexdigest()==moneyhash)
 f.client('hold','networkClose','unpaid')
 with f.rpc_pin():
  f.check('pinned-RPC-positive-control',f.client('trial','networkClose')['state']=='AVAILABLE')
  with f.network():
   r=f.client('unavailable','networkClose');f.check('rpc-isolation-new-payment-not-accepted',not r.get('accepted',False),r);f.client('cancel','networkClose');v=f.order('networkClose');f.check('rpc-isolation-no-charge-no-release',v['payments']==v['released']==0 and v['reservation']=='HELD',v);f.sample('rpc-isolated')
 f.closed('networkClose')
 f.client('hold','redisClose','unpaid')
 with f.down('redis'):
  r=f.client('unavailable','redisClose');f.check('redis-down-new-payment-not-accepted',not r.get('accepted',False),r);f.client('cancel','redisClose');v=f.order('redisClose');f.check('redis-down-no-charge-no-release',v['payments']==v['released']==0 and v['reservation']=='HELD',v);f.sample('redis-stopped')
 f.closed('redisClose')
 # Disable only ordinary refund execution/release temporarily; natural expiry and reconciliation remain active.
 with f.refund_pause() as pause:
  for name in ('refundBlocked','refundHealthy'):
   f.client('hold',name,name);f.client('create',name);f.client('choose',name);f.wait('paid-before-expiry-'+name,lambda n=name:f.order(n),lambda v:v['successful']==v['accepted']==1)
  refundorders=[f.oid(n) for n in ('refundBlocked','refundHealthy')];ids=','.join("'"+x+"'" for x in refundorders)
  refundsql=f"SELECT JSON_ARRAYAGG(JSON_OBJECT('refundId',refund_id,'orderId',order_id,'eligibility',eligibility_status,'basis',eligibility_basis,'funds',funds_status,'sync',sync_status,'release',release_status)) FROM zj_market_b06.b_refund WHERE order_id IN ({ids});"
  refs=f.wait('natural-expiry-complete-eligible-refunds',lambda:f.jsonquery(refundsql),lambda v:v is not None and len(v)==2 and all(r['eligibility']=='ELIGIBLE' and r['basis']=='TEAM_FAILED_ACCEPTED' and r['funds']=='NONE' for r in v),240)
  mapping={r['orderId']:r['refundId'] for r in refs};blocked=mapping[refundorders[0]];healthy=mapping[refundorders[1]]
  (f.work/'refunds.properties').write_text(f'blocked={blocked}\nhealthy={healthy}\nblockedOrder={refundorders[0]}\nhealthyOrder={refundorders[1]}\n')
  with f.down('marketing-a',kill=True):
   f.refund_tool('drop-response');f.sample('refund-unknown-A-down')
   f.wait('unknown-refund-task-due',lambda:int(f.query(f"SELECT COUNT(*) FROM zj_market_b06.b_refund_task WHERE refund_id='{blocked}' AND next_attempt_ms<=UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000;")),lambda v:v==1,45)
   f.refund_tool('isolate');f.check('unknown-refund-isolation-no-stock-release',all(f.order(n)['released']==0 for n in ('refundBlocked','refundHealthy')))
   keysql=f"SELECT refund_id,attempt_id,request_hash FROM zj_market_b06.b_refund_attempt WHERE refund_id IN ('{blocked}','{healthy}') ORDER BY refund_id,attempt_id;";keys=f.query(keysql)
   f.restore(pause)
   v=f.wait('original-refund-and-independent-release-while-A-down',lambda:f.jsonquery(refundsql),lambda v:len(v)==2 and all(r['funds']=='SUCCEEDED' and r['release']=='RELEASED' and r['sync']!='ACCEPTED' for r in v),150)
   f.check('unknown-refund-kept-original-attempt',keys==f.query(keysql));f.sample('refund-release-before-A-sync')
  f.wait('refund-A-sync-after-recovery',lambda:f.jsonquery(refundsql),lambda v:all(r['sync']=='ACCEPTED' for r in v),180)
  f.check('refund-recovery-attempts-unchanged',keys==f.query(keysql))
 f.transport();f.transport('bad-secret');f.transport('denied-topic');f.transport('bad-ca');f.transport();f.transport('signed',True);f.transport('bad-hmac',True);f.transport('no-client',True);f.transport('bad-client',True);f.transport('signed',True)
 # Final proof reads actual channel, A quotas, immutable fact bodies and unique stock ledgers.
 facts={}
 for name,goods in f.fixture()['goods'].items():
  inv=f.jsonquery(f"SELECT JSON_OBJECT('available',available,'reserved',reserved,'sold',sold) FROM zj_market_b06.b_inventory_account WHERE goods_id='{goods}';");f.check('final-stock-'+name,inv==({'available':8,'reserved':0,'sold':2} if name=='success' else {'available':10,'reserved':0,'sold':0}),inv);facts[name]={'inventory':inv,'orders':[]}
 for name,order in f.fixture()['orders'].items():
  oid=order['orderId'];v=f.order(name);isrefund=name.startswith('refund');success=name in ('first','second')
  f.check('unique-terminal-'+name,v['status']==('GROUP_COMPLETED' if success else 'CLOSED') and v['confirmed']==v['fulfillments']==(1 if success else 0) and v['released']==(0 if success else 1) and v['successful']==v['accepted']==(1 if success or isrefund else 0),v)
  channel=f.jsonquery(f"SELECT JSON_OBJECT('payments',(SELECT COUNT(*) FROM zj_market_b06.b_sim_attempt sa JOIN zj_market_b06.b_payment p ON p.payment_id=sa.payment_id WHERE p.order_id='{oid}' AND sa.state='SUCCEEDED' AND sa.paid_at_ms=p.paid_at_ms),'refunds',(SELECT COUNT(*) FROM zj_market_b06.b_sim_refund_attempt sa JOIN zj_market_b06.b_refund r ON r.refund_id=sa.refund_id WHERE r.order_id='{oid}' AND sa.state='SUCCEEDED'),'paid',(SELECT COALESCE(SUM(amount),0) FROM zj_market_b06.b_payment WHERE order_id='{oid}' AND funds_state='SUCCEEDED'),'refunded',(SELECT COALESCE(SUM(amount),0) FROM zj_market_b06.b_refund WHERE order_id='{oid}' AND funds_status='SUCCEEDED'),'releaseProofs',(SELECT COUNT(*) FROM zj_market_b06.b_refund_release WHERE order_id='{oid}'),'unownedBlocks',(SELECT COUNT(*) FROM zj_market_b06.b_order_block WHERE order_id='{oid}' AND state='ACTIVE' AND kind<>'RECONCILIATION'),'unfinishedRefundWork',(SELECT COUNT(*) FROM zj_market_b06.b_trade_work WHERE order_id='{oid}' AND kind='REFUND_OBLIGATION' AND state<>'DONE'));")
  f.check('channel-conservation-'+name,channel['payments']==(1 if success or isrefund else 0) and channel['refunds']==channel['releaseProofs']==(1 if isrefund else 0) and float(channel['paid'])==(90 if success or isrefund else 0) and float(channel['refunded'])==(90 if isrefund else 0) and channel['unownedBlocks']==channel['unfinishedRefundWork']==0,channel)
  team=order['teamId'];quota=f.jsonquery(f"SELECT JSON_OBJECT('status',team_status,'reserved',reserved_count,'paid',paid_count,'target',target_count,'actualReserved',(SELECT COUNT(*) FROM group_buy_market_b06.ab_trade_order o WHERE o.team_id=t.team_id AND o.order_status IN ('RESERVED','PAID')),'actualPaid',(SELECT COUNT(*) FROM group_buy_market_b06.ab_trade_order o WHERE o.team_id=t.team_id AND o.order_status='PAID')) FROM group_buy_market_b06.ab_team t WHERE team_id='{team}';")
  expected=2 if success else 1 if isrefund else 0;f.check('A-exact-quota-'+name,quota['reserved']==quota['paid']==quota['actualReserved']==quota['actualPaid']==expected and quota['target']==2 and (not success or quota['status']=='COMPLETED') and (not isrefund or quota['status']=='FAILED'),quota)
  if isrefund:
   recon=f.jsonquery(f"SELECT JSON_OBJECT('state',t.state,'members',(SELECT COUNT(*) FROM zj_market_b06.b_reconciliation_member m WHERE m.task_id=t.task_id),'finalized',(SELECT COUNT(*) FROM zj_market_b06.b_reconciliation_member m WHERE m.task_id=t.task_id AND m.finalized=1),'submission',s.state) FROM zj_market_b06.b_reconciliation_task t JOIN zj_market_b06.b_reconciliation_submission s ON s.task_id=t.task_id WHERE t.team_id='{team}';");f.check('complete-roster-reconciliation-'+name,recon['state']=='RESOLVED' and recon['members']==recon['finalized'] and recon['submission']=='ACKNOWLEDGED',recon)
   notification=f.jsonquery(f"SELECT JSON_OBJECT('accepted',(SELECT COUNT(*) FROM zj_market_b06.b_trade_inbox i WHERE i.event_type='TEAM_RECONCILIATION_REQUIRED' AND JSON_UNQUOTE(JSON_EXTRACT(CONVERT(i.body USING utf8mb4),'$.payload.teamId'))='{team}' AND i.body_hash=SHA2(i.body,256) AND JSON_UNQUOTE(JSON_EXTRACT(CONVERT(i.body USING utf8mb4),'$.payload.rosterVersion'))=(SELECT roster_version FROM group_buy_market_b06.ab_team WHERE team_id='{team}')),'quarantined',(SELECT COUNT(*) FROM zj_market_b06.b_trade_quarantine q WHERE JSON_UNQUOTE(JSON_EXTRACT(CONVERT(q.body USING utf8mb4),'$.payload.teamId'))='{team}'));");f.check('actual-opaque-roster-notification-accepted-'+name,notification['accepted']==1 and notification['quarantined']==0,notification)
  facts[next(k for k,g in f.fixture()['goods'].items() if g==order['goods'])]['orders'].append({'name':name,'orderId':oid,'paymentId':order.get('paymentId'),'attemptId':order.get('attemptId'),'terminal':v,'channel':channel,'aQuota':quota})
 f.check('old-financial-facts-unchanged',hashlib.sha256(f.query(oldsql).encode()).hexdigest()==oldhash)
 f.check('shared-containers-unchanged',shared()==others);f.check('hosts-unchanged',hashlib.sha256(hosts.read_bytes()).hexdigest()==hosthash)
 for service,initial in baseline.items():
  final=f.inspect(service);f.check('runtime-restored-'+service,final['image']==initial['image'] and final['restart']==initial['restart'] and final['command']==initial['command'] and final['extraHosts']==initial['extraHosts'] and not final['state']['OOMKilled'])
 f.d.ready();f.run('actual-readiness',['node',ROOT/'docs/tests/b06-startup-client.mjs','ready',ROOT/'.local/b06/control',ROOT/'.local/b06/runtime'],timeout=150)
 latest=f.sample('final');f.check('final-seven-and-HTTPS-healthy',latest['complete']);f.report['facts']=facts;f.report['toolImages']=f.toolimages;f.report['scope']='Windows Docker dedicated containers; real SIGKILL/stop/rpc-network disconnect; simulated channel response loss through verification only';f.report['linuxVmValidated']=False;f.report['gitPublished']=False;f.save()
