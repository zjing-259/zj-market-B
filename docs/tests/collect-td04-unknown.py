"""Read-only conservation check for the TD-04 lost-response/restart order."""
from pathlib import Path
import argparse,datetime,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);a=p.parse_args()
 if not re.fullmatch(r'td04_[0-9]{8}_[0-9]{2}',a.run_name):raise ValueError('Invalid batch')
 work=ROOT/'target/team-discovery'/a.run_name;f=json.loads((work/'unknown-fixture.json').read_text())
 for key in ('goodsId','orderId','teamId'):
  if not re.fullmatch('[a-f0-9-]{36}',f[key]):raise ValueError('Invalid ID')
 for mode in ('unknown-send','unknown-recover'):
  if json.loads((work/('race-'+mode+'-report.json')).read_text())['status']!='PASSED':raise RuntimeError(mode+' failed')
 project='zj-market-'+a.run_name.replace('_','-')
 def sql(query):
  r=subprocess.run(['docker','--context','desktop-linux','exec','-i',project+'-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names'],input=query,capture_output=True,text=True,timeout=60)
  if r.returncode:raise RuntimeError('SQL failed '+r.stderr[-200:])
  return r.stdout.strip()
 goods,oid,team=f['goodsId'],f['orderId'],f['teamId']
 inv=json.loads(sql(f"SELECT JSON_OBJECT('available',available,'reserved',reserved,'sold',sold) FROM zj_market_b06.b_inventory_account WHERE goods_id='{goods}';"))
 assert inv=={'available':10,'reserved':0,'sold':0},inv
 b=json.loads(sql(f"SELECT JSON_OBJECT('status',o.business_status,'reservation',r.state,'intent',o.purchase_intent_id,'releaseLedgers',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='RELEASE'),'confirmLedgers',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='CONFIRM'),'payments',(SELECT COUNT(*) FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id),'ordersForIntent',(SELECT COUNT(*) FROM zj_market_b06.b_market_order other WHERE other.purchase_intent_id=o.purchase_intent_id AND other.user_id=o.user_id)) FROM zj_market_b06.b_market_order o JOIN zj_market_b06.b_inventory_reservation r ON r.order_id=o.order_id WHERE o.order_id='{oid}';"))
 assert b=={'status':'CLOSED','reservation':'RELEASED','intent':f['intent'],'releaseLedgers':1,'confirmLedgers':0,'payments':0,'ordersForIntent':1},b
 aorder=sql(f"SELECT CONCAT(order_status,'|',team_id,'|',IFNULL(payment_id,'')) FROM group_buy_market_b06.ab_trade_order WHERE source='b06' AND channel='web' AND out_trade_no='{oid}';")
 assert aorder.startswith(('CANCELLED|'+team+'|','EXPIRED|'+team+'|')) and aorder.endswith('|'),aorder
 report={'stage':'TD-04','status':'PASSED_UNKNOWN_RECOVERY_ACCOUNTING_SUBSET','stageCompletion':False,'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inventory':inv,'B':b,'AOrder':aorder,'checks':['response-lost-original-business-key','B-restart-same-order','A-team-preserved','one-release-no-funds-no-duplicate-order']}
 (work/'unknown-accounting-report.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS TD04 unknown recovery accounting subset')
if __name__=='__main__':main()
