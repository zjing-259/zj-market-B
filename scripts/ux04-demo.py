"""Add two owned UX demo samples; never updates historical products, activities or trades."""
from pathlib import Path
import importlib.util
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
if ROOT.name != 'zj-market-ux':
    raise RuntimeError('UX worktree required')
spec = importlib.util.spec_from_file_location('ux_deployment', ROOT / 'scripts/b06-deployment.py')
deployment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deployment)
if deployment.PROJECT != 'zj-market-ux':
    raise RuntimeError('Unexpected deployment owner')
d = deployment.Deployment('desktop-linux')
state = d.ready()
if state.get('mode') != 'open' or state.get('phase') != 'READY' or d.gateway_mode() != 'open':
    raise RuntimeError('Actual open UX required')
work = ROOT / '.local/ux04'
work.mkdir(parents=True, exist_ok=True)

def stable_snapshot():
    names = ['zj-market-b06-' + name + '-1' for name in ['mysql', 'redis', 'namesrv', 'broker', 'marketing-a', 'market-b', 'web']]
    identities = subprocess.check_output(d.docker + ['inspect', '--format', '{{.Id}} {{.Image}}', *names], text=True)
    sql = "SELECT 'products',COUNT(*) FROM zj_market_b06.b_product UNION ALL SELECT 'stock-ledger',COUNT(*) FROM zj_market_b06.b_inventory_ledger UNION ALL SELECT 'orders',COUNT(*) FROM zj_market_b06.b_market_order UNION ALL SELECT 'payments',COUNT(*) FROM zj_market_b06.b_payment UNION ALL SELECT 'refunds',COUNT(*) FROM zj_market_b06.b_refund UNION ALL SELECT 'teams',COUNT(*) FROM group_buy_market_b06.ab_team UNION ALL SELECT 'a-orders',COUNT(*) FROM group_buy_market_b06.ab_trade_order;"
    counts = subprocess.check_output(d.docker + ['exec', '-i', 'zj-market-b06-mysql-1', 'sh', '-c',
        'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --skip-column-names'], input=sql, text=True)
    return {'containers': identities.splitlines(), 'counts': counts.splitlines()}

before = stable_snapshot()
subprocess.run(['node', 'scripts/ux04-demo.mjs', 'prepare'], cwd=ROOT, check=True)
file = work / 'demo-fixture.json'
fixture = json.loads(file.read_text(encoding='utf-8'))
if not all(item.get('activityId') for item in fixture['items']):
    base = int(d.admin('ux04-new-activity-id', 'SELECT GREATEST(640000,COALESCE(MAX(activity_id),0))+1 FROM group_buy_market_b06.group_buy_activity;').strip())
    for index, item in enumerate(fixture['items']):
        item['activityId'] = base + index
        item['discountId'] = (base + index) * 100 + 1
        item['validMinutes'] = 120
    file.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for item in fixture['items']:
    goods = item['goodsId']
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', goods):
        raise RuntimeError('Invalid owned goods ID')
    activity, discount = int(item['activityId']), int(item['discountId'])
    expected = f'{activity}\t{discount}\t120\t{goods}'
    existing = d.admin('ux04-existing-config', f"SELECT a.activity_id,a.discount_id,a.valid_time,s.goods_id FROM group_buy_market_b06.group_buy_activity a JOIN group_buy_market_b06.sc_sku_activity s ON s.activity_id=a.activity_id WHERE a.activity_id={activity} AND s.source='b06' AND s.channel='web';").strip()
    if existing:
        if existing != expected:
            raise RuntimeError('Existing configuration differs; refusing changes')
        continue
    sql = f"USE group_buy_market_b06; START TRANSACTION; INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) VALUES ('{discount}','UX04 demo','Ten yuan reduction',0,'ZJ','10'); INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time) VALUES ({activity},'UX04 demo','{discount}',1,10,2,120,1,UTC_TIMESTAMP()-INTERVAL 1 HOUR,UTC_TIMESTAMP()+INTERVAL 30 DAY); INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES ('b06','web',{activity},'{goods}'); COMMIT;"
    d.admin('ux04-insert-new-config', sql)
subprocess.run(['node', 'scripts/ux04-demo.mjs', 'verify'], cwd=ROOT, check=True)
after = stable_snapshot()
if before != after:
    raise RuntimeError('Stable snapshot changed; inspect before claiming acceptance')
report = {'status': 'PASS', 'project': 'zj-market-ux', 'stableUnchanged': True, 'before': before,
          'after': after, 'products': [{k: item[k] for k in ['goodsId', 'name', 'activityId', 'validMinutes']} for item in fixture['items']]}
(work / 'demo-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('UX04_DEMO_PASS two-new-samples/120-minute-teams/old-site-unchanged')
