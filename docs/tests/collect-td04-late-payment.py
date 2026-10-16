"""Verify a pre-deadline channel payment delivered to A after the team deadline."""
from pathlib import Path
from decimal import Decimal
import argparse,datetime,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);a=p.parse_args()
 if not re.fullmatch(r'td04_[0-9]{8}_[0-9]{2}',a.run_name):raise ValueError('Invalid batch')
 work=ROOT/'target/team-discovery'/a.run_name;f=json.loads((work/'expiry-fixture.json').read_text());end=json.loads((work/'race-expiry-final-report.json').read_text());result=json.loads((work/'race-expiry-result-report.json').read_text())
 assert end['status']==result['status']=='PASSED' and end['terminal']=='GROUP_COMPLETED'
 goods,team=f['goodsId'],f['teamId'];ids=[f['openId'],f['joinId']]
 if not all(re.fullmatch('[a-f0-9-]{36}',x) for x in [goods,team,*ids]):raise ValueError('Invalid ID')
 project='zj-market-'+a.run_name.replace('_','-')
 def query(sql):
  r=subprocess.run(['docker','--context','desktop-linux','exec','-i',project+'-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names'],input=sql,capture_output=True,text=True,timeout=60)
  if r.returncode:raise RuntimeError('SQL failed '+r.stderr[-200:])
  return r.stdout.strip()
 def obj(sql):return json.loads(query(sql))
 inv=obj(f"SELECT JSON_OBJECT('available',available,'reserved',reserved,'sold',sold) FROM zj_market_b06.b_inventory_account WHERE goods_id='{goods}';")
 assert inv=={'available':8,'reserved':0,'sold':2},inv
 ateam=obj(f"SELECT JSON_OBJECT('status',team_status,'target',target_count,'paid',paid_count,'reserved',reserved_count,'deadline',DATE_FORMAT(valid_end_time,'%Y-%m-%dT%H:%i:%s.%fZ'),'resolved',DATE_FORMAT(resolved_at,'%Y-%m-%dT%H:%i:%s.%fZ')) FROM group_buy_market_b06.ab_team WHERE team_id='{team}';")
 assert ateam['status']=='COMPLETED' and ateam['target']==ateam['paid']==ateam['reserved']==2,ateam
 assert ateam['resolved']>ateam['deadline'],ateam
 facts={}
 for oid in ids:
  aorder=obj(f"SELECT JSON_OBJECT('status',order_status,'paymentId',payment_id,'paidAmount',paid_amount,'paidAt',DATE_FORMAT(paid_at,'%Y-%m-%dT%H:%i:%s.%fZ'),'refundId',refund_id) FROM group_buy_market_b06.ab_trade_order WHERE source='b06' AND channel='web' AND out_trade_no='{oid}';")
  assert aorder['status']=='PAID' and aorder['paymentId'] and not aorder['refundId'] and Decimal(str(aorder['paidAmount']))==90,aorder
  assert aorder['paidAt']<ateam['deadline'],aorder
  b=obj(f"SELECT JSON_OBJECT('status',o.business_status,'reservation',r.state,'confirmLedgers',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='CONFIRM'),'releaseLedgers',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='RELEASE'),'payments',(SELECT COUNT(*) FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id AND p.funds_state='SUCCEEDED' AND p.a_acceptance='ACCEPTED'),'refunds',(SELECT COUNT(*) FROM zj_market_b06.b_refund rf WHERE rf.order_id=o.order_id),'fulfillment',(SELECT COUNT(*) FROM zj_market_b06.b_fulfillment ff WHERE ff.order_id=o.order_id AND ff.status='PENDING')) FROM zj_market_b06.b_market_order o JOIN zj_market_b06.b_inventory_reservation r ON r.order_id=o.order_id WHERE o.order_id='{oid}';")
  assert b=={'status':'GROUP_COMPLETED','reservation':'CONFIRMED','confirmLedgers':1,'releaseLedgers':0,'payments':1,'refunds':0,'fulfillment':1},b
  channel=obj(f"SELECT JSON_OBJECT('paidRoots',(SELECT COUNT(*) FROM zj_market_b06.b_sim_payment sp JOIN zj_market_b06.b_payment p ON p.payment_id=sp.payment_id WHERE p.order_id='{oid}' AND sp.gate='PAID'),'successfulAttempts',(SELECT COUNT(*) FROM zj_market_b06.b_sim_attempt sa JOIN zj_market_b06.b_payment p ON p.payment_id=sa.payment_id WHERE p.order_id='{oid}' AND sa.state='SUCCEEDED'));")
  assert channel=={'paidRoots':1,'successfulAttempts':1},channel
  facts[oid]={'A':aorder,'B':b,'channel':channel}
 second=facts[f['joinId']]['A']['paidAt']
 assert second<ateam['deadline']<ateam['resolved']
 out={'stage':'TD-04','status':'PASSED_LATE_A_PAYMENT_EVENT_ACCOUNTING','stageCompletion':False,'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'isolatedBrokerStoppedUntilAfterDeadline':True,'secondChannelPaidAt':second,'aTeam':ateam,'inventory':inv,'orders':facts,'checks':['channel-paid-before-deadline','A-completed-after-deadline','no-false-failure-or-refund','two-unique-inventory-confirms','two-pending-fulfillments']}
 (work/'late-payment-accounting-report.json').write_text(json.dumps(out,indent=2)+'\n')
 print('PASS TD04 late A payment event accounting')
if __name__=='__main__':main()
