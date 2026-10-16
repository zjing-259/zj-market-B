"""Run a fresh real-browser transaction batch against the owned main443 stack."""
from pathlib import Path
import argparse
import json
import os
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OLD = Path('D:/Java/zj-market-b-06')
DOCKER = ['docker', '--context', 'desktop-linux']


def call(args, *, input_text=None, timeout=600):
    result = subprocess.run([str(x) for x in args], input=input_text,
                            capture_output=True, text=True, encoding='utf-8',
                            errors='replace', timeout=timeout)
    if result.returncode:
        raise RuntimeError('TD-06.3 command failed: ' + ' '.join(str(x) for x in args[:4]))
    return result.stdout


def main(name):
    if not re.fullmatch(r'td06_3_main_[0-9]{8}_[0-9]{2}', name):
        raise ValueError('Invalid TD-06.3 batch name')
    work = ROOT / 'target/team-discovery' / name
    if not work.is_dir() or (work / 'browser').exists():
        raise RuntimeError('Batch missing or browser already started; recover original operations, do not repeat')
    call(['python', '-B', ROOT / 'scripts/td06-environment.py', 'ready', '--target', 'main443'])
    browser = work / 'browser'
    env = os.environ.copy()
    env.update(B06_BROWSER_WORK=str(browser),
               B06_BROWSER_CONTROL=str(OLD / '.local/b06/control'),
               B06_BROWSER_RUNTIME=str(OLD / '.local/b06/runtime'),
               B06_BROWSER_STAGE='TD-06.3')
    with (work / 'prepare.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(['node', 'docs/tests/td06-3-real-browser.mjs', 'prepare', name],
                                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    if result.returncode:
        raise RuntimeError('Product preparation failed; inspect private log and original fixture')
    fixture = json.loads((browser / 'fixture.json').read_text(encoding='utf-8'))
    sql_command = DOCKER + ['exec', '-i', 'zj-market-b06-mysql-1', 'sh', '-c',
                            'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names']
    base = int(call(sql_command, input_text="SELECT GREATEST(900000,COALESCE(MAX(activity_id),0))+1 FROM group_buy_market_b06.group_buy_activity;").strip())
    for offset, (kind, goods) in enumerate(fixture['goods'].items()):
        if not re.fullmatch(r'[a-f0-9-]{36}', goods):
            raise RuntimeError('Invalid product fixture')
        activity = base + offset
        discount = activity * 100 + 1
        minutes = 2 if kind == 'expiry' else 30
        sql = ("USE group_buy_market_b06; START TRANSACTION; "
               f"INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) VALUES ('{discount}','TD06.3 {kind}','Ten yuan reduction',0,'ZJ','10'); "
               f"INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time) VALUES ({activity},'TD06.3 {kind}','{discount}',1,10,2,{minutes},1,UTC_TIMESTAMP()-INTERVAL 1 HOUR,UTC_TIMESTAMP()+INTERVAL 30 DAY); "
               f"INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES ('b06','web',{activity},'{goods}'); COMMIT;")
        call(sql_command, input_text=sql)
        fixture.setdefault('activities', {})[kind] = {'activityId': activity, 'discountId': discount, 'validMinutes': minutes}
        (browser / 'fixture.json').write_text(json.dumps(fixture, indent=2) + '\n', encoding='utf-8')
    print('PASS fresh-main443-products-and-activities', flush=True)
    with (work / 'browser.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(['node', 'docs/tests/td06-3-real-browser.mjs', 'browser', name],
                                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    if result.returncode:
        raise RuntimeError('Real browser flow failed; inspect private browser log and screenshots; do not restart batch')
    report = json.loads((browser / 'browser-report.json').read_text(encoding='utf-8'))
    if report['status'] != 'PASSED':
        raise RuntimeError('Browser report failed')
    print('PASS main443-real-browser-' + str(len(report['checks'])) + '-checks', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-name', required=True)
    main(parser.parse_args().run_name)
