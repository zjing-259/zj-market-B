"""Run the real current A/B/Web TD-05 flow in a previously prepared owned clone."""
from pathlib import Path
import argparse, json, os, re, subprocess

ROOT = Path(__file__).resolve().parents[2]
DOCKER = ['docker','--context','desktop-linux']

def call(args, *, input=None, timeout=600):
    r = subprocess.run([str(x) for x in args], input=input, capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=timeout)
    if r.returncode: raise RuntimeError('Command failed; inspect private batch logs: '+str(args[:4]))
    return r.stdout

def main(name, suffix):
    if not re.fullmatch(r'td05_[0-9]{8}_[0-9]{2}', name): raise ValueError('Invalid batch')
    work = ROOT / 'target/team-discovery' / name
    state = json.loads((work / 'prepare-report.json').read_text(encoding='utf-8'))
    if state['status'] != 'READY': raise RuntimeError('TD05 stack not ready')
    project = state['project']
    browser_dir = work / ('browser' + suffix)
    if suffix:
        browser_dir.mkdir(exist_ok=False)
        (browser_dir/'fixture.json').write_bytes((work/'browser/fixture.json').read_bytes())
    fixture_path = browser_dir / 'fixture.json'
    fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
    if fixture.get('activities') and not suffix: raise RuntimeError('Fixture activities already created')
    query = "SELECT GREATEST(740000,COALESCE(MAX(activity_id),0))+1 FROM group_buy_market_b06.group_buy_activity;"
    sql_command = DOCKER + ['exec','-i',project+'-mysql-1','sh','-c',
                            'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names']
    base = int(call(sql_command,input=query).strip()) if not suffix else 0
    for offset, (kind, goods) in enumerate(fixture['goods'].items() if not suffix else []):
        if not re.fullmatch(r'[a-f0-9-]{36}',goods): raise RuntimeError('Invalid product fixture')
        activity = base + offset
        discount = activity * 100 + 1
        minutes = 2 if kind == 'expiry' else 15
        sql = ("USE group_buy_market_b06; START TRANSACTION; "
               f"INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) VALUES ('{discount}','TD05 {kind}','Ten yuan reduction',0,'ZJ','10'); "
               f"INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time) VALUES ({activity},'TD05 {kind}','{discount}',1,10,2,{minutes},1,UTC_TIMESTAMP()-INTERVAL 1 HOUR,UTC_TIMESTAMP()+INTERVAL 30 DAY); "
               f"INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES ('b06','web',{activity},'{goods}'); COMMIT;")
        call(sql_command,input=sql)
        fixture.setdefault('activities',{})[kind]={'activityId':activity,'discountId':discount,'validMinutes':minutes}
        fixture_path.write_text(json.dumps(fixture,indent=2)+'\n',encoding='utf-8')
    print('PASS td05-owned-activities' if not suffix else 'PASS td05-existing-activities-validated',flush=True)
    env=os.environ.copy()
    env.update(B06_BROWSER_WORK=str(browser_dir),B06_BROWSER_CONTROL=str(work/'private/control'),
               B06_BROWSER_RUNTIME=str(work/'private/runtime'),B06_BROWSER_STAGE='TD-05')
    with (work/('browser'+suffix+'.log')).open('w',encoding='utf-8') as log:
        result=subprocess.run(['node','docs/tests/td05-real-browser.mjs','browser',name],cwd=ROOT,
                              env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    if result.returncode: raise RuntimeError('Real browser flow failed; inspect ignored browser.log and screenshots')
    report=json.loads((browser_dir/'browser-report.json').read_text(encoding='utf-8'))
    if report['status']!='PASSED':raise RuntimeError('Browser report not passed')
    print('PASS td05-real-browser-'+str(len(report['checks']))+'-checks',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-name',required=True)
    p.add_argument('--evidence-suffix',default='')
    args=p.parse_args()
    if args.evidence_suffix and not re.fullmatch(r'[0-9]{2}',args.evidence_suffix):raise ValueError('Use two-digit evidence suffix')
    main(args.run_name,args.evidence_suffix)

