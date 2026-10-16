"""Prove repeated real HTTPS discovery GETs leave selected A/B trade facts unchanged."""
from pathlib import Path
import argparse, datetime, hashlib, json, re, subprocess

ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);a=p.parse_args()
 if not re.fullmatch(r'td04_[0-9]{8}_[0-9]{2}',a.run_name):raise RuntimeError('Invalid TD04 batch')
 work=ROOT/'target/team-discovery'/a.run_name
 race=json.loads((work/'race-race-report.json').read_text());team=race['teamId'];goods=race['goodsId'];ids=list(race['orders'].values())[:2]+race['orders']['losers']
 ids=[race['orders']['open'],race['orders']['winner'],*race['orders']['losers']]
 if not all(re.fullmatch(r'[a-f0-9-]{36}',x) for x in [team,goods,*ids]):raise RuntimeError('Invalid ID')
 project='zj-market-'+a.run_name.replace('_','-')
 docker=['docker','--context','desktop-linux']
 where='('+','.join("'"+x+"'" for x in ids)+')'
 queries={
  'A-team':f"SELECT * FROM group_buy_market_b06.ab_team WHERE team_id='{team}' ORDER BY team_id;",
  'A-orders':f"SELECT * FROM group_buy_market_b06.ab_trade_order WHERE team_id='{team}' ORDER BY out_trade_no;",
  'B-orders':f"SELECT * FROM zj_market_b06.b_market_order WHERE order_id IN {where} ORDER BY order_id;",
  'B-inventory':f"SELECT * FROM zj_market_b06.b_inventory_account WHERE goods_id='{goods}' ORDER BY goods_id;",
  'B-reservations':f"SELECT * FROM zj_market_b06.b_inventory_reservation WHERE order_id IN {where} ORDER BY order_id;",
  'B-ledgers':f"SELECT * FROM zj_market_b06.b_inventory_ledger WHERE order_id IN {where} ORDER BY order_id,kind;",
  'B-payments':f"SELECT * FROM zj_market_b06.b_payment WHERE order_id IN {where} ORDER BY order_id;",
  'B-refunds':f"SELECT * FROM zj_market_b06.b_refund WHERE order_id IN {where} ORDER BY order_id;",
 }
 def snap():
  result={}
  for label,query in queries.items():
   r=subprocess.run(docker+['exec','-i',project+'-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names'],input=query,capture_output=True,text=True,timeout=60)
   if r.returncode:raise RuntimeError('SQL failed '+label+' '+r.stderr[-200:])
   result[label]=hashlib.sha256(r.stdout.encode()).hexdigest()
  return result
 before=snap()
 run=subprocess.run(['node',str(ROOT/'docs/tests/td04-race.mjs'),'readonly',str(work)],capture_output=True,text=True,timeout=120)
 (work/'readonly-console.log').write_text(run.stdout+run.stderr)
 if run.returncode:raise RuntimeError('HTTPS GET test failed; see readonly-console.log')
 after=snap()
 assert before==after, {key:(before[key],after[key]) for key in before if before[key]!=after[key]}
 browser=json.loads((work/'race-readonly-report.json').read_text())
 assert browser['status']=='PASSED' and len([x for x in browser['checks'] if x.startswith('readonly-discovery-')])==25
 out={'stage':'TD-04','status':'PASSED_READONLY_GET_CONSERVATION','stageCompletion':False,'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'requests':25,'tables':list(queries),'beforeSha256':before,'afterSha256':after,'getReportSha256':hashlib.sha256((work/'race-readonly-report.json').read_bytes()).hexdigest()}
 (work/'readonly-accounting-report.json').write_text(json.dumps(out,indent=2)+'\n')
 print('PASS TD04 25 real GETs: A/B trade facts unchanged')
if __name__=='__main__':main()
