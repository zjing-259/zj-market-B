"""Create fresh TD-00 schemas in owned MySQL; never alter B-06 rows or migrations.

This prepares data only. Schema clones are NOT Flyway migration acceptance, and
seeded A projections are NOT evidence of real MQ sync or real accepted payments.
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKER = ['docker', '--context', 'desktop-linux']
CONTAINER = 'zj-market-b06-mysql-1'


def sql(text):
    r = subprocess.run(DOCKER+['exec', '-i', CONTAINER, 'sh', '-c',
        'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --skip-column-names --raw'],
        input='SET time_zone="+00:00";\n'+text, text=True, encoding='utf-8', capture_output=True, timeout=90)
    if r.returncode:
        # Query text and stderr can contain fixture credentials. Do not print either.
        code = re.search(r'ERROR \d+ \([A-Z0-9]+\) at line \d+', r.stderr)
        constraint = re.search(r"Check constraint '([a-zA-Z0-9_]+)'", r.stderr)
        raise RuntimeError('TD00 SQL failed: '+(code.group() if code else 'unknown code')
                           + (' constraint='+constraint.group(1) if constraint else '')
                           + '; no existing schemas cleaned or reset')
    return r.stdout


def tables(db):
    return sql(f"SELECT table_name FROM information_schema.tables WHERE table_schema='{db}' AND table_type='BASE TABLE' ORDER BY table_name;").splitlines()


def fingerprint(db, selected=None):
    """Hash canonical primary-key-ordered dumps; only hashes/counts leave memory."""
    r = subprocess.run(DOCKER+['exec', CONTAINER, 'sh', '-c',
        'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysqldump -uroot --no-create-info '
        '--skip-extended-insert --order-by-primary --skip-comments --skip-add-locks '
        '--skip-disable-keys --no-tablespaces --set-gtid-purged=OFF '+db+(' '+' '.join(selected) if selected else '')],
        capture_output=True, timeout=90)
    if r.returncode:
        raise RuntimeError('Read-only protected data snapshot failed')
    inserts = b'\n'.join(line for line in r.stdout.splitlines() if line.startswith(b'INSERT INTO'))
    return {'sha256': hashlib.sha256(inserts).hexdigest().upper(), 'rowStatements': len(inserts.splitlines())}


def clone(source, target):
    definitions = []
    for name in tables(source):
        if not re.fullmatch('[a-z0-9_]+', name):
            raise ValueError('Unexpected table name')
        ddl = sql(f'SHOW CREATE TABLE `{source}`.`{name}`;').split('\t', 1)[1].strip()
        ddl = re.sub(r' AUTO_INCREMENT=\d+', '', ddl)
        definitions.append(ddl+';')
    sql(f'CREATE DATABASE `{target}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin; USE `{target}`; SET FOREIGN_KEY_CHECKS=0;\n'+'\n'.join(definitions)+'\nSET FOREIGN_KEY_CHECKS=1;')
    return len(definitions)


def prepare(run, work, java_home, check_dir, libs):
    if not re.fullmatch('td00_[0-9]{8}_[0-9]{2}', run):
        raise ValueError('Fresh name required: td00_YYYYMMDD_NN')
    work.mkdir(parents=True, exist_ok=False)
    private = ROOT/'.local/team-discovery'/run
    private.mkdir(parents=True, exist_ok=False)
    # Explicit NTFS private-material protection, no global/repository ACL changes.
    if os.name == 'nt':
        identity = subprocess.check_output(['whoami', '/user', '/fo', 'csv', '/nh'], text=True).split(',')[1].strip().strip('"')
        r = subprocess.run(['icacls', str(private), '/inheritance:r', '/grant:r',
                            '*'+identity+':(OI)(CI)F', '*S-1-5-18:(OI)(CI)F', '*S-1-5-32-544:(OI)(CI)F'], capture_output=True)
        if r.returncode: raise RuntimeError('Private fixture ACL failed')
    row = json.loads(subprocess.check_output(DOCKER+['inspect', CONTAINER], text=True))[0]
    assert row['Config']['Labels']['com.docker.compose.project']=='zj-market-b06'
    assert row['Config']['Labels']['com.docker.compose.service']=='mysql'
    protected = ['group_buy_market_b06', 'zj_market_b06']
    before = {d: fingerprint(d) for d in protected}
    # Running B06 schedulers may legitimately update task/attempt control metadata.
    # Preserve whole-db observations but assert unchanged durable money/order/stock facts.
    core = {protected[0]: ['ab_team','ab_trade_order','ab_payment_guard','ab_exception_payment'],
            protected[1]: ['b_market_order','b_inventory_account','b_inventory_reservation','b_inventory_ledger',
                           'b_purchase_guard','b_payment','b_sim_payment','b_sim_attempt','b_sim_refund',
                           'b_sim_refund_attempt','b_refund','b_refund_release','b_fulfillment']}
    financial_before = {d:fingerprint(d, names) for d,names in core.items()}
    a, b = 'group_buy_market_'+run, 'zj_market_'+run
    assert sql(f"SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name IN ('{a}','{b}');").strip()=='0', 'Never reuse fixture schemas'
    schemas = {a: clone(protected[0], a), b: clone(protected[1], b)}
    accounts = []
    for name in ['owner','viewer','rival','operator']:
        accounts.append({'name':run+'_'+name, 'userId':str(uuid.uuid4()), 'password':secrets.token_urlsafe(24), 'roles':['USER','OPERATOR'] if name=='operator' else ['USER']})
    cp = str(check_dir)+os.pathsep+str(libs/'*')
    r = subprocess.run([str(java_home/'bin/java.exe'), '-cp', cp, 'FixturePasswords'],
                       input='\n'.join(x['password'] for x in accounts)+'\n', text=True, capture_output=True, timeout=60)
    if r.returncode: raise RuntimeError('Fixture password hashing failed')
    hashes = r.stdout.splitlines()
    assert len(hashes)==len(accounts) and all(x.startswith('{argon2id}$argon2id$') for x in hashes)
    (private/'accounts.json').write_text(json.dumps(accounts,indent=2)+'\n')
    goods = str(uuid.uuid4())
    # IDs unique within this entirely new schema; no old activity is extended.
    activity, discount = 714001, '71400001'
    inserts = [f'USE `{b}`; START TRANSACTION; SET @now=CAST(UNIX_TIMESTAMP(UTC_TIMESTAMP(3))*1000 AS SIGNED);']
    for account, hashed in zip(accounts, hashes):
        uid = account['userId']
        inserts.append(f"INSERT INTO b_user(user_id,login_name,display_name,password_hash) VALUES ('{uid}','{account['name']}','TD00 {account['roles'][0]}','{hashed}');")
        for role in account['roles']: inserts.append(f"INSERT INTO b_user_role(user_id,role) VALUES ('{uid}','{role}');")
    op = accounts[-1]['userId'];operation,ledger = str(uuid.uuid4()),str(uuid.uuid4())
    inserts += [f"INSERT INTO b_product(goods_id,goods_name,description,original_price,currency,sale_status,product_version,created_at_ms,updated_at_ms) VALUES ('{goods}','TD00 discovery fixture','Isolated baseline fixture',100.00,'CNY','ON_SALE',1,@now,@now);",
        f"INSERT INTO b_inventory_account(goods_id,available,reserved,sold,inventory_version,initialized_by,created_at_ms,updated_at_ms) VALUES ('{goods}',100,0,0,2,'TD00_FIXTURE',@now,@now);",
        f"INSERT INTO b_inventory_operation(operation_id,operator_id,operation_key,goods_id,kind,delta,expected_version,reason,outcome,result_code,completed_at_ms,result_available,result_reserved,result_sold,result_version,result_updated_at_ms,request_hash) VALUES ('{operation}','{op}','td00-inbound','{goods}','INBOUND',100,1,'TD00 isolated preparation','SUCCEEDED','0000',@now,100,0,0,2,@now,SHA2(CONCAT_WS(CHAR(10),'{op}','INBOUND','{goods}','100','1','TD00 isolated preparation'),256));",
        f"INSERT INTO b_inventory_ledger(ledger_id,goods_id,operation_id,business_key,kind,delta_available,before_available,after_available,before_reserved,after_reserved,before_sold,after_sold,reason,created_at_ms) VALUES ('{ledger}','{goods}','{operation}','{operation}','INBOUND',100,0,100,0,0,0,0,'TD00 isolated preparation',@now);", 'COMMIT;',
        f'USE `{a}`; START TRANSACTION;',
        f"INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) VALUES ('{discount}','TD00 discount','Isolated fixture',0,'ZJ','10');",
        f"INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time) VALUES ({activity},'TD00 discovery','{discount}',1,20,3,120,1,UTC_TIMESTAMP()-INTERVAL 1 HOUR,UTC_TIMESTAMP()+INTERVAL 30 DAY);",
        f"INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES ('td00','web',{activity},'{goods}');", 'COMMIT;']
    sql('\n'.join(inserts))
    facts = {'stage':'TD-00','runName':run,'status':'PREPARED_ISOLATED_FIXTURE','schemas':schemas,
             'schemaProvenance':'DDL-only clone of actual B06 schemas; not Flyway acceptance; empty history',
             'source':'td00','channel':'web','goodsId':goods,'productVersion':'1','activityId':str(activity),
             'discountId':discount,'targetCount':3,'teamValidMinutes':120,'stock':100,
             'accounts':[{k:v for k,v in x.items() if k!='password'} for x in accounts],
             'sync':'NOT_SENT; product Outbox and A projection empty; real sync belongs to TD01/02',
             'business':'No order, team, reservation, channel payment/refund or team event seeded'}
    facts['activityWindow'] = sql(f'SELECT start_time,end_time FROM `{a}`.group_buy_activity WHERE activity_id={activity};').strip()
    after = {d: fingerprint(d) for d in protected}
    facts['originalBefore'] = before; facts['originalAfter'] = after
    facts['originalDataUnchanged'] = before==after
    facts['protectedFinancialTables'] = core
    facts['financialBefore'] = financial_before
    facts['financialAfter'] = {d:fingerprint(d,names) for d,names in core.items()}
    facts['originalFinancialUnchanged'] = facts['financialBefore']==facts['financialAfter']
    for db in [a,b]:
        facts.setdefault('fixtureBaselines',{})[db]=fingerprint(db)
    (work/'fixture.json').write_text(json.dumps(facts,indent=2)+'\n')
    assert facts['originalFinancialUnchanged'], 'Original money/order/stock changed; preserve evidence and diagnose'
    print(json.dumps({'status':facts['status'],'schemas':schemas,'originalFinancialUnchanged':True,
                      'wholeDatabaseBytesUnchanged':facts['originalDataUnchanged'],'credentials':'private .local only'}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-name',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--java-home',type=Path,required=True)
    p.add_argument('--check-classes',type=Path,required=True)
    p.add_argument('--libs',type=Path,required=True)
    a=p.parse_args()
    try:
        prepare(a.run_name,a.output,a.java_home,a.check_classes,a.libs)
    except Exception as error:
        if a.output.exists():
            (a.output/'FAILED.json').write_text(json.dumps({'stage':'TD-00','status':'FAILED','error':str(error)})+'\n')
        raise
