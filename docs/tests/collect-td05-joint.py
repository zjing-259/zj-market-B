"""Read-only A/B conservation checks for a TD-05 isolated browser batch."""
from pathlib import Path
import argparse,importlib.util,json,hashlib,datetime,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);p.add_argument('--evidence-suffix',default='')
 a=p.parse_args()
 if not re.fullmatch(r'td05_[0-9]{8}_[0-9]{2}',a.run_name) or a.evidence_suffix and not re.fullmatch(r'[0-9]{2}',a.evidence_suffix):raise RuntimeError('Invalid TD05 batch')
 batch=ROOT/'target/team-discovery'/a.run_name
 work=batch/('browser'+a.evidence_suffix)
 project='zj-market-'+a.run_name.replace('_','-')
 assert work.resolve().is_relative_to(batch.resolve())
 f=json.loads((work/'fixture.json').read_text());browser=json.loads((work/'browser-report.json').read_text())
 assert browser['status']=='PASSED' and browser['httpsBypass'] is False
 assert browser['browserScriptSha256']==hashlib.sha256((ROOT/'docs/tests/td05-real-browser.mjs').read_bytes()).hexdigest(), 'Browser source changed since execution'
 docker=['docker','--context','desktop-linux']
 def admin(sql):
  r=subprocess.run(docker+['exec','-i',project+'-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names'],input=sql,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
  if r.returncode:raise RuntimeError('TD05 read-only SQL failed')
  return r.stdout
 assert admin("SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema='group_buy_market_b06' AND index_name IN ('idx_ab_team_discovery','idx_ab_order_discovery_owner');").strip()=='10'
 checks=[];facts={}
 def query(name,sql):return json.loads(admin(sql).strip())
 for name,goods in f['goods'].items():
  assert re.fullmatch('[a-f0-9-]{36}',goods)
  inv=query(name+'-inventory',f"SELECT JSON_OBJECT('available',available,'reserved',reserved,'sold',sold) FROM zj_market_b06.b_inventory_account WHERE goods_id='{goods}';")
  assert inv==({'available':8,'reserved':0,'sold':2} if name=='success' else {'available':10,'reserved':0,'sold':0})
  checks.append(name+'-stock-conservation');facts[name]={'goodsId':goods,'inventory':inv,'orders':[]}
  orders=[oid for oid,o in browser['orders'].items() if o['goods']==goods];assert len(orders)==(2 if name=='success' else 1)
  for oid in orders:
   assert re.fullmatch('[A-Za-z0-9_-]{1,64}',oid)
   sql=f"SELECT JSON_OBJECT('status',o.business_status,'review',o.review_required,'lastError',o.last_error,'reservation',r.state,'fulfillments',(SELECT COUNT(*) FROM zj_market_b06.b_fulfillment ff WHERE ff.order_id=o.order_id AND ff.status='PENDING'),'confirmLedgers',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='CONFIRM'),'releaseLedgers',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='RELEASE'),'payments',(SELECT COUNT(*) FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id AND p.funds_state='SUCCEEDED' AND p.a_acceptance='ACCEPTED'),'paidAmount',(SELECT COALESCE(SUM(p.amount),0) FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id AND p.funds_state='SUCCEEDED'),'channelSuccesses',(SELECT COUNT(*) FROM zj_market_b06.b_sim_attempt sa JOIN zj_market_b06.b_payment p ON p.payment_id=sa.payment_id WHERE p.order_id=o.order_id AND sa.state='SUCCEEDED'),'refundedAmount',(SELECT COALESCE(SUM(amount),0) FROM zj_market_b06.b_refund rf WHERE rf.order_id=o.order_id AND rf.funds_status='SUCCEEDED' AND rf.sync_status='ACCEPTED' AND rf.release_status='RELEASED'),'refundReleaseRows',(SELECT COUNT(*) FROM zj_market_b06.b_refund_release rr WHERE rr.order_id=o.order_id)) FROM zj_market_b06.b_market_order o JOIN zj_market_b06.b_inventory_reservation r ON r.order_id=o.order_id WHERE o.order_id='{oid}';"
   v=query(name+'-'+oid,sql)
   if name!='expiry':assert not v['review']
   else:assert not v['review'] or v['lastError'] in ('TEAM_FAILED','TEAM_RECONCILIATION_REQUIRED')
   from decimal import Decimal
   if name=='success':assert v['status']=='GROUP_COMPLETED' and v['reservation']=='CONFIRMED' and v['fulfillments']==1 and v['confirmLedgers']==1 and v['releaseLedgers']==0 and v['payments']==v['channelSuccesses']==1 and Decimal(str(v['paidAmount']))==90 and Decimal(str(v['refundedAmount']))==0
   else:
    assert v['status']=='CLOSED' and v['reservation']=='RELEASED' and v['fulfillments']==v['confirmLedgers']==0 and v['releaseLedgers']==1
    if name=='expiry':assert v['payments']==v['channelSuccesses']==v['refundReleaseRows']==1 and Decimal(str(v['paidAmount']))==Decimal(str(v['refundedAmount']))==90
    else:assert v['payments']==v['channelSuccesses']==v['refundReleaseRows']==0 and Decimal(str(v['paidAmount']))==Decimal(str(v['refundedAmount']))==0
   block=query(name+'-review-ownership-'+oid,f"SELECT JSON_OBJECT('unownedActive',(SELECT COUNT(*) FROM zj_market_b06.b_order_block WHERE order_id='{oid}' AND state='ACTIVE' AND kind<>'RECONCILIATION'),'reviewFinancialWork',(SELECT COUNT(*) FROM zj_market_b06.b_trade_work WHERE order_id='{oid}' AND state='REVIEW_REQUIRED'),'unfinishedRefundWork',(SELECT COUNT(*) FROM zj_market_b06.b_trade_work WHERE order_id='{oid}' AND kind='REFUND_OBLIGATION' AND state<>'DONE'));")
   assert block['unownedActive']==block['reviewFinancialWork']==block['unfinishedRefundWork']==0
   v['reviewOwnership']=block
   channel=query(name+'-channel-'+oid,f"SELECT JSON_OBJECT('paidRoots',(SELECT COUNT(*) FROM zj_market_b06.b_sim_payment sp JOIN zj_market_b06.b_payment p ON p.payment_id=sp.payment_id WHERE p.order_id='{oid}' AND sp.gate='PAID' AND sp.amount=p.amount),'refundSuccesses',(SELECT COUNT(*) FROM zj_market_b06.b_sim_refund_attempt sa JOIN zj_market_b06.b_refund rf ON rf.refund_id=sa.refund_id WHERE rf.order_id='{oid}' AND sa.state='SUCCEEDED'),'refundedAmount',(SELECT COALESCE(SUM(sr.refunded_amount),0) FROM zj_market_b06.b_sim_refund sr JOIN zj_market_b06.b_refund rf ON rf.refund_id=sr.refund_id WHERE rf.order_id='{oid}'),'paidTimeMatches',(SELECT COUNT(*) FROM zj_market_b06.b_sim_attempt sa JOIN zj_market_b06.b_payment p ON p.payment_id=sa.payment_id WHERE p.order_id='{oid}' AND sa.state='SUCCEEDED' AND sa.paid_at_ms=p.paid_at_ms));")
   assert channel['paidRoots']==channel['paidTimeMatches']==(0 if name=='cancel' else 1)
   assert channel['refundSuccesses']==(1 if name=='expiry' else 0) and Decimal(str(channel['refundedAmount']))==(90 if name=='expiry' else 0)
   af=query(name+'-A-order-'+oid,f"SELECT JSON_OBJECT('paymentId',payment_id,'paidAmount',paid_amount,'refundId',refund_id,'refundStatus',refund_status,'refundAmount',refund_amount) FROM group_buy_market_b06.ab_trade_order WHERE source='b06' AND channel='web' AND out_trade_no='{oid}';")
   if name=='cancel':assert af['paymentId'] is None and af['refundId'] is None
   else:
    assert af['paymentId'] and Decimal(str(af['paidAmount']))==90
    if name=='expiry':assert af['refundId'] and af['refundStatus']=='SUCCEEDED' and Decimal(str(af['refundAmount']))==90
    else:assert af['refundId'] is None
   facts[name]['orders'].append({'orderId':oid,**v,'channel':channel,'aAcceptedFacts':af});checks.append('funds-stock-unique-'+oid)
  team=browser['orders'][orders[0]]['teamId'];assert re.fullmatch('[A-Za-z0-9_-]{1,64}',team)
  av=query(name+'-A-team',f"SELECT JSON_OBJECT('teamId',team_id,'status',team_status,'target',target_count,'complete',paid_count,'locked',reserved_count,'expired',valid_end_time<=UTC_TIMESTAMP()) FROM group_buy_market_b06.ab_team WHERE team_id='{team}';")
  quota=query(name+'-A-exact-quota',f"SELECT JSON_OBJECT('reserved',(SELECT COUNT(*) FROM group_buy_market_b06.ab_trade_order WHERE team_id='{team}' AND order_status IN ('RESERVED','PAID')),'paid',(SELECT COUNT(*) FROM group_buy_market_b06.ab_trade_order WHERE team_id='{team}' AND order_status='PAID'));")
  assert 0<=av['complete']<=av['locked']<=av['target'] and av['locked']==quota['reserved'] and av['complete']==quota['paid']
  assert av['locked']==av['complete']==(2 if name=='success' else 1 if name=='expiry' else 0)
  facts[name]['exactAQuota']=quota
  if name=='success':assert av['status']=='COMPLETED' and av['complete']==2 and av['target']==2
  if name=='expiry':
   assert av['status']=='FAILED' and av['expired']==1
   recon=query('expiry-reconciliation',f"SELECT JSON_OBJECT('state',t.state,'members',(SELECT COUNT(*) FROM zj_market_b06.b_reconciliation_member mm WHERE mm.task_id=t.task_id),'finalized',(SELECT COUNT(*) FROM zj_market_b06.b_reconciliation_member mm WHERE mm.task_id=t.task_id AND mm.finalized=1),'submission',s.state) FROM zj_market_b06.b_reconciliation_task t JOIN zj_market_b06.b_reconciliation_submission s ON s.task_id=t.task_id WHERE t.team_id='{team}';")
   assert recon['state']=='RESOLVED' and recon['members']==recon['finalized'] and recon['submission']=='ACKNOWLEDGED';facts[name]['reconciliation']=recon
  facts[name]['aTeam']=av;checks.append(name+'-actual-A-quota-terminal')
 containers=json.loads(subprocess.check_output(docker+['inspect']+[project+'-'+x+'-1' for x in ['mysql','redis','namesrv','broker','marketing-a','market-b','web']],text=True))
 assert all(c['State']['Health']['Status']=='healthy' and not c['State']['OOMKilled'] for c in containers)
 checks.append('seven-services-healthy-no-observed-oom')
 sources=['docs/tests/td05-real-browser.mjs','docs/tests/run-td05-joint.py','docs/tests/collect-td05-joint.py','docs/tests/prepare-td05-stack.py']
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 report={'stage':'TD-05','status':'PASSED_REAL_BROWSER_ACCOUNTING_SUBSET','stageCompletion':False,'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runName':a.run_name,'project':project,'scope':'Windows isolated A/B databases and MQ; real Edge TLS verification; simulated funds only','browserChecks':browser['checks'],'accountingChecks':checks,'facts':facts,'rawBrowserReportSha256':sha(work/'browser-report.json'),'sourceSha256':{s:sha(ROOT/s) for s in sources},'images':{c['Config']['Labels']['com.docker.compose.service']:c['Image'] for c in containers},'screenshots':{p.name:sha(p) for p in work.glob('*.png')},'gitPublished':False}
 (work/'accounting-report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS TD05 browser accounting subset')
if __name__=='__main__':main()

