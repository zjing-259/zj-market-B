"""Verify the real expiry/payment-submission race settles without unaccounted funds."""
from pathlib import Path
from decimal import Decimal
import argparse,datetime,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);a=p.parse_args()
 if not re.fullmatch(r'td04_[0-9]{8}_[0-9]{2}',a.run_name):raise ValueError('Invalid batch')
 work=ROOT/'target/team-discovery'/a.run_name
 fixture=json.loads((work/'expiry-fixture-02.json').read_text());final=json.loads((work/'race-expiry-final-02-report.json').read_text());submitted=json.loads((work/'race-expiry-result-02-report.json').read_text())
 assert final['status']==submitted['status']=='PASSED' and final['terminal']=='CLOSED'
 goods,team,opening,joining=(fixture[x] for x in ('goodsId','teamId','openId','joinId'))
 if not all(re.fullmatch(r'[a-f0-9-]{36}',x) for x in (goods,team,opening,joining)):raise ValueError('Invalid ID')
 project='zj-market-'+a.run_name.replace('_','-')
 def query(sql):
  r=subprocess.run(['docker','--context','desktop-linux','exec','-i',project+'-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names'],input=sql,capture_output=True,text=True,timeout=60)
  if r.returncode:raise RuntimeError('SQL failed '+r.stderr[-200:])
  return r.stdout.strip()
 def obj(sql):return json.loads(query(sql))
 inventory=obj(f"SELECT JSON_OBJECT('available',available,'reserved',reserved,'sold',sold) FROM zj_market_b06.b_inventory_account WHERE goods_id='{goods}';")
 assert inventory=={'available':10,'reserved':0,'sold':0},inventory
 a_team=obj(f"SELECT JSON_OBJECT('status',team_status,'paid',paid_count,'reserved',reserved_count,'target',target_count) FROM group_buy_market_b06.ab_team WHERE team_id='{team}';")
 assert a_team=={'status':'FAILED','paid':1,'reserved':1,'target':2},a_team
 facts={}
 for oid,paid in ((opening,True),(joining,False)):
  b=obj(f"SELECT JSON_OBJECT('status',o.business_status,'reservation',r.state,'confirmLedgers',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='CONFIRM'),'releaseLedgers',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='RELEASE'),'funds',(SELECT funds_state FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id),'acceptance',(SELECT a_acceptance FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id),'paidAmount',(SELECT COALESCE(SUM(p.amount),0) FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id AND p.funds_state='SUCCEEDED'),'refundAmount',(SELECT COALESCE(SUM(rf.amount),0) FROM zj_market_b06.b_refund rf WHERE rf.order_id=o.order_id AND rf.funds_status='SUCCEEDED' AND rf.sync_status='ACCEPTED' AND rf.release_status='RELEASED')) FROM zj_market_b06.b_market_order o JOIN zj_market_b06.b_inventory_reservation r ON r.order_id=o.order_id WHERE o.order_id='{oid}';")
  assert b['status']=='CLOSED' and b['reservation']=='RELEASED' and b['confirmLedgers']==0 and b['releaseLedgers']==1,b
  assert b['funds']==('SUCCEEDED' if paid else 'UNPAID') and b['acceptance']==('ACCEPTED' if paid else 'NOT_SENT'),b
  assert Decimal(str(b['paidAmount']))==Decimal(str(b['refundAmount']))==(90 if paid else 0),b
  channel=obj(f"SELECT JSON_OBJECT('paidRoots',(SELECT COUNT(*) FROM zj_market_b06.b_sim_payment sp JOIN zj_market_b06.b_payment p ON p.payment_id=sp.payment_id WHERE p.order_id='{oid}' AND sp.gate='PAID'),'successfulAttempts',(SELECT COUNT(*) FROM zj_market_b06.b_sim_attempt sa JOIN zj_market_b06.b_payment p ON p.payment_id=sa.payment_id WHERE p.order_id='{oid}' AND sa.state='SUCCEEDED'),'closedUnpaidAttempts',(SELECT COUNT(*) FROM zj_market_b06.b_sim_attempt sa JOIN zj_market_b06.b_payment p ON p.payment_id=sa.payment_id WHERE p.order_id='{oid}' AND sa.state='CLOSED_UNPAID'),'refundSuccesses',(SELECT COUNT(*) FROM zj_market_b06.b_sim_refund_attempt sa JOIN zj_market_b06.b_refund rf ON rf.refund_id=sa.refund_id WHERE rf.order_id='{oid}' AND sa.state='SUCCEEDED'));")
  assert channel['paidRoots']==channel['successfulAttempts']==channel['refundSuccesses']==(1 if paid else 0),channel
  if not paid:assert channel['closedUnpaidAttempts']==1,channel
  af=query(f"SELECT CONCAT(order_status,'|',IFNULL(refund_status,'')) FROM group_buy_market_b06.ab_trade_order WHERE source='b06' AND channel='web' AND out_trade_no='{oid}';")
  assert af==('PAID|SUCCEEDED' if paid else 'CANCELLED|'),af
  facts[oid]={'B':b,'channel':channel,'A':af}
 out={'stage':'TD-04','status':'PASSED_EXPIRY_PAYMENT_RACE_ACCOUNTING','stageCompletion':False,'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'submittedBeforeDeadline':submitted['paidAt']<datetime.datetime.fromisoformat(fixture['deadline'].replace('Z','+00:00')).timestamp()*1000,'meaning':'Client simulated-result submission was accepted before expiry; channel ultimately closed the second attempt unpaid. First paid order was fully refunded.','inventory':inventory,'aTeam':a_team,'orders':facts}
 assert out['submittedBeforeDeadline']
 (work/'expiry-race-accounting-02-report.json').write_text(json.dumps(out,indent=2)+'\n')
 print('PASS TD04 expiry/payment race accounting')
if __name__=='__main__':main()
