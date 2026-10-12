"""Collect new B063 browser + real database conservation evidence; never mutates business data."""
from pathlib import Path
import argparse,importlib.util,json,hashlib,datetime,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True)
 for option in ['work-dir','project','control','runtime','compose','deployment-root','output','stage']:p.add_argument('--'+option)
 a=p.parse_args()
 isolated=any([a.project,a.control,a.runtime,a.compose,a.deployment_root])
 if isolated:
  assert all([a.project,a.control,a.runtime,a.compose,a.deployment_root,a.work_dir,a.output,a.stage]), 'Complete isolated scope required'
  assert re.fullmatch(r'zj-market-b066-[a-z0-9-]{1,40}',a.project), 'Invalid isolated ownership'
  for value in [a.control,a.runtime,a.compose,a.deployment_root,a.work_dir]:assert Path(value).resolve().is_relative_to((ROOT/'.local/b06/backups').resolve()), 'Unsafe isolated path'
 if not re.fullmatch(r'b063-[a-z0-9-]+',a.run_name):raise RuntimeError('Invalid batch')
 work=Path(a.work_dir) if a.work_dir else ROOT/'.local/b06/browser'/a.run_name;f=json.loads((work/'fixture.json').read_text());browser=json.loads((work/'browser-report.json').read_text())
 assert browser['status']=='PASSED' and browser['httpsBypass'] is False
 assert browser['browserScriptSha256']==hashlib.sha256((ROOT/'docs/tests/b06-normal-browser.mjs').read_bytes()).hexdigest(), 'Browser source changed since execution'
 spec=importlib.util.spec_from_file_location('deployment',ROOT/'scripts/b06-deployment.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 if isolated:
  m.PROJECT=a.project;m.CONTROL=Path(a.control);m.RUNTIME=Path(a.runtime);m.ROOT=Path(a.deployment_root)
 d=m.Deployment('desktop-linux')
 if isolated:d.compose=d.docker+['compose','-p',a.project,'-f',a.compose]
 d.ready()
 checks=[];facts={}
 def query(name,sql):return json.loads(d.admin('b063-'+name,sql).strip())
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
 containers=json.loads(d.run('b063-final-containers',d.docker+['inspect']+[(a.project or 'zj-market-b06')+'-'+x+'-1' for x in ['mysql','redis','namesrv','broker','marketing-a','market-b','web']]))
 assert all(c['State']['Health']['Status']=='healthy' and not c['State']['OOMKilled'] for c in containers)
 checks.append('seven-services-healthy-no-observed-oom')
 sources=['scripts/open-b06-browser.ps1','docs/tests/b06-normal-browser.mjs','docs/tests/run-b06-normal.py','docs/tests/collect-b06-normal.py']
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 report={'stage':a.stage or 'B-06.3','status':'PASSED_WINDOWS_REAL_BROWSER_NORMAL_FLOW','stageCompletion':True,'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runName':a.run_name,'scope':'Windows Docker; real Edge TLS verification enabled; dedicated resolver; simulated funds only','browserChecks':browser['checks'],'accountingChecks':checks,'facts':facts,'rawBrowserReportSha256':sha(work/'browser-report.json'),'sourceSha256':{s:sha(ROOT/s) for s in sources},'images':{c['Config']['Labels']['com.docker.compose.service']:c['Image'] for c in containers},'screenshots':{p.name:sha(p) for p in work.glob('*.png')},'linuxVmValidated':False,'gitPublished':False}
 (work/'accounting-report.json').write_text(json.dumps(report,indent=2)+'\n');(Path(a.output) if a.output else ROOT/'docs/tests/b06-normal-acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS B063 browser and accounting closeout')
if __name__=='__main__':main()
