"""Explicit release batches; add owned fixtures only, never reset historic facts."""
from pathlib import Path
import argparse, json, re, subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('action', choices=['prepare', 'browser', 'collect'])
p.add_argument('--target', required=True, choices=['ux', 'main'])
p.add_argument('--batch', required=True)
a = p.parse_args()
if ROOT.name != 'zj-market-ux' or not re.fullmatch(r'ux05-[0-9]{8}-[0-9]{2}', a.batch):
    raise RuntimeError('Owned worktree and batch required')
project = 'zj-market-ux' if a.target == 'ux' else 'zj-market-b06'
work = ROOT / '.local/ux05' / (a.batch + '-' + a.target)
docker = ['docker', '--context', 'desktop-linux']

def sql(statement):
    r = subprocess.run(docker + ['exec', '-i', project + '-mysql-1', 'sh', '-c',
        'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names'],
        input=statement, capture_output=True, text=True, encoding='utf-8', timeout=90)
    if r.returncode:
        raise RuntimeError('Owned fixture SQL rejected; no automatic replacements')
    return r.stdout.strip()

if a.action == 'prepare':
    subprocess.run(['node', 'scripts/ux05-browser.mjs', 'prepare', a.target, a.batch], cwd=ROOT, check=True)
    file = work / 'fixture.json'
    fixture = json.loads(file.read_text(encoding='utf-8'))
    if not fixture.get('activities'):
        base = int(sql('SELECT GREATEST(650000,COALESCE(MAX(activity_id),0))+1 FROM group_buy_market_b06.group_buy_activity;'))
        fixture['activities'] = {name: {'id': base + i, 'discount': (base + i)*100+1, 'minutes': 2 if name == 'expiry' else 30}
                                 for i, name in enumerate(fixture['goods'])}
        file.write_text(json.dumps(fixture, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for kind, goods in fixture['goods'].items():
        if not re.fullmatch(r'[a-f0-9-]{36}', goods):
            raise RuntimeError('Invalid owned goods ID')
        config = fixture['activities'][kind]
        activity, discount, minutes = int(config['id']), int(config['discount']), int(config['minutes'])
        previous = sql(f"SELECT a.activity_id,a.discount_id,a.valid_time,s.goods_id FROM group_buy_market_b06.group_buy_activity a JOIN group_buy_market_b06.sc_sku_activity s ON s.activity_id=a.activity_id WHERE a.activity_id={activity} AND s.source='b06' AND s.channel='web';")
        if previous:
            if previous != f'{activity}\t{discount}\t{minutes}\t{goods}':
                raise RuntimeError('Existing activity differs; refusing overwrite')
            continue
        sql(f"USE group_buy_market_b06; START TRANSACTION; INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) VALUES ('{discount}','UX05 acceptance','Ten yuan reduction',0,'ZJ','10'); INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time) VALUES ({activity},'UX05 acceptance','{discount}',1,10,2,{minutes},1,UTC_TIMESTAMP()-INTERVAL 1 HOUR,UTC_TIMESTAMP()+INTERVAL 30 DAY); INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES ('b06','web',{activity},'{goods}'); COMMIT;")
    print('UX05_CONFIGURED ' + a.target)
elif a.action == 'browser':
    subprocess.run(['node', 'scripts/ux05-browser.mjs', 'browser', a.target, a.batch], cwd=ROOT, check=True)
else:
    subprocess.run(['py', '-B', 'scripts/ux05-accounting.py', '--target', a.target, '--batch', a.batch], cwd=ROOT, check=True)
