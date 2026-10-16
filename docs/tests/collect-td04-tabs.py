"""Check two concurrent sessions for the same SKU create one recoverable obligation."""
from pathlib import Path
import argparse,datetime,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);a=p.parse_args()
 if not re.fullmatch(r'td04_[0-9]{8}_[0-9]{2}',a.run_name):raise ValueError('Invalid batch')
 work=ROOT/'target/team-discovery'/a.run_name;f=json.loads((work/'tabs-fixture.json').read_text());r=json.loads((work/'race-tabs-report.json').read_text())
 assert r['status']=='PASSED' and len(f['orders'])==1 and f['rejected']==['ACTIVE_PURCHASE_EXISTS']
 goods,oid=f['goodsId'],f['orders'][0]
 if not all(re.fullmatch('[a-f0-9-]{36}',x) for x in (goods,oid)):raise ValueError('Invalid ID')
 project='zj-market-'+a.run_name.replace('_','-')
 def query(sql):
  x=subprocess.run(['docker','--context','desktop-linux','exec','-i',project+'-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names'],input=sql,capture_output=True,text=True,timeout=60)
  if x.returncode:raise RuntimeError('SQL failed '+x.stderr[-200:])
  return x.stdout.strip()
 inv=json.loads(query(f"SELECT JSON_OBJECT('available',available,'reserved',reserved,'sold',sold) FROM zj_market_b06.b_inventory_account WHERE goods_id='{goods}';"))
 assert inv=={'available':10,'reserved':0,'sold':0},inv
 b=json.loads(query(f"SELECT JSON_OBJECT('status',o.business_status,'reservation',r.state,'orders',(SELECT COUNT(*) FROM zj_market_b06.b_market_order other WHERE other.goods_id=o.goods_id AND other.user_id=o.user_id),'releaseLedgers',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='RELEASE'),'confirmLedgers',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='CONFIRM'),'payments',(SELECT COUNT(*) FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id)) FROM zj_market_b06.b_market_order o JOIN zj_market_b06.b_inventory_reservation r ON r.order_id=o.order_id WHERE o.order_id='{oid}';"))
 assert b=={'status':'CLOSED','reservation':'RELEASED','orders':1,'releaseLedgers':1,'confirmLedgers':0,'payments':0},b
 aorder=query(f"SELECT CONCAT(order_status,'|',IFNULL(payment_id,'')) FROM group_buy_market_b06.ab_trade_order WHERE source='b06' AND channel='web' AND out_trade_no='{oid}';")
 assert aorder in ('CANCELLED|','EXPIRED|'),aorder
 report={'stage':'TD-04','status':'PASSED_TWO_TAB_GUARD_ACCOUNTING','stageCompletion':False,'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'goodsId':goods,'orderId':oid,'rejected':f['rejected'],'inventory':inv,'B':b,'A':aorder}
 (work/'tabs-accounting-report.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS TD04 two-tab same-SKU accounting')
if __name__=='__main__':main()
