"""Attach one two-seat activity to the TD-04-owned race product."""
from pathlib import Path
import argparse,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);p.add_argument('--fixture-name',default='race-fixture.json',choices=['race-fixture.json','unknown-fixture.json','expiry-fixture.json','tabs-fixture.json']);p.add_argument('--valid-minutes',type=int,default=15);a=p.parse_args()
if not re.fullmatch(r'td04_[0-9]{8}_[0-9]{2}',a.run_name):raise ValueError('Invalid batch')
if not 1<=a.valid_minutes<=15:raise ValueError('Invalid isolated activity duration')
work=ROOT/'target/team-discovery'/a.run_name
project=json.loads((work/'prepare-report.json').read_text())['project']
fixture=work/a.fixture_name;f=json.loads(fixture.read_text())
if 'activityId' in f:raise RuntimeError('TD04 activity already created')
goods=f['goodsId']
if not re.fullmatch(r'[a-f0-9-]{36}',goods):raise ValueError('Invalid product')
command=['docker','--context','desktop-linux','exec','-i',project+'-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names']
def query(sql):
 r=subprocess.run(command,input=sql,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
 if r.returncode:raise RuntimeError('TD04 clone SQL failed')
 return r.stdout.strip()
activity=int(query('SELECT GREATEST(750000,COALESCE(MAX(activity_id),0))+1 FROM group_buy_market_b06.group_buy_activity;'))
discount=activity*100+1
query("USE group_buy_market_b06; START TRANSACTION; "
      f"INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) VALUES ('{discount}','TD04 last slot','Ten yuan reduction',0,'ZJ','10'); "
      f"INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time) VALUES ({activity},'TD04 last slot','{discount}',1,10,2,{a.valid_minutes},1,UTC_TIMESTAMP()-INTERVAL 1 HOUR,UTC_TIMESTAMP()+INTERVAL 30 DAY); "
      f"INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES ('b06','web',{activity},'{goods}'); COMMIT;")
f.update(activityId=activity,discountId=discount)
fixture.write_text(json.dumps(f,indent=2)+'\n')
print('PASS td04-race-activity-created')
