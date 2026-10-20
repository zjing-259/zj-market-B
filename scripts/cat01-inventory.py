"""CAT-01.1 read-only A/B snapshot and exact fixture ownership collection."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,subprocess

ROOT=Path(__file__).resolve().parents[1]
STABLE=Path('D:/Java/zj-market-stable')
DOCKER=['docker','--context','desktop-linux']

def sha(file):return hashlib.sha256(Path(file).read_bytes()).hexdigest().upper()
def write(file,value):file.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sql(project,statement):
    # Every data connection is transaction-read-only, independently of query text.
    command="SET SESSION TRANSACTION READ ONLY; START TRANSACTION WITH CONSISTENT SNAPSHOT; SELECT JSON_OBJECT('readOnlyGuard',@@transaction_read_only); "+statement+' COMMIT;'
    r=subprocess.run(DOCKER+['exec','-i',project+'-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --default-character-set=utf8mb4 --batch --raw --skip-column-names'],input=command,capture_output=True,text=True,encoding='utf-8',timeout=120)
    if r.returncode:raise RuntimeError('Read-only inventory SQL failed; private output withheld')
    rows=[json.loads(line) for line in r.stdout.splitlines() if line]
    assert rows and rows[0]=={'readOnlyGuard':1},'MySQL transaction is not read-only'
    return rows[1:]

# Full rows are kept privately, without identity credentials or user identifiers.
TABLES={
 'products':('zj_market_b06.b_product','goods_id,goods_name,description,image_url,original_price,currency,sale_status,product_version'),
 'sync':('zj_market_b06.b_product_sync','goods_id,target_version,target_event_id,confirmed_version,state,last_error'),
 'inventory':('zj_market_b06.b_inventory_account','goods_id,available,reserved,sold,inventory_version'),
 'projection':('group_buy_market_b06.ab_product_projection','source,channel,goods_id,product_version,goods_name,original_price,currency,sale_status,content_hash'),
 'bindings':('group_buy_market_b06.sc_sku_activity','source,channel,activity_id,goods_id'),
 'activities':('group_buy_market_b06.group_buy_activity','activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time,tag_id,tag_scope'),
 'discounts':('group_buy_market_b06.group_buy_discount','discount_id,discount_name,discount_type,market_plan,market_expr,tag_id'),
 'orders':('zj_market_b06.b_market_order','order_id,goods_id,quantity,original_price,deduction_price,pay_price,currency,business_status,order_version,review_required,last_error,closed_at_ms,close_basis'),
 'payments':('zj_market_b06.b_payment','payment_id,order_id,goods_id,amount,currency,funds_state,gate,a_acceptance,active_attempt_id,success_attempt_id,paid_at_ms,version,review_required,last_error'),
 'refunds':('zj_market_b06.b_refund','refund_id,order_id,payment_id,team_id,amount,currency,eligibility_status,funds_status,version,sync_status,release_status'),
 'teams':('group_buy_market_b06.ab_team','team_id,source,channel,activity_id,goods_id,target_count,reserved_count,paid_count,team_status,team_version,valid_start_time,valid_end_time'),
 'aOrders':('group_buy_market_b06.ab_trade_order','source,channel,out_trade_no,order_id,goods_id,activity_id,product_version,team_id,original_price,deduction_price,pay_price,order_status,record_version,payment_id,paid_amount,refund_id,refund_status,refund_amount'),
 'work':('zj_market_b06.b_trade_work','work_id,kind,business_key,order_id,payment_id,team_id,state,reasons'),
 'blocks':('zj_market_b06.b_order_block','order_id,kind,owner_id,state,reason'),
 'fulfillment':('zj_market_b06.b_fulfillment','order_id,goods_id,team_id,status,snapshot_hash'),
 'ledger':('zj_market_b06.b_inventory_ledger','ledger_id,goods_id,operation_id,kind,delta_available,before_available,after_available,before_reserved,after_reserved,before_sold,after_sold'),
 'reservations':('zj_market_b06.b_inventory_reservation','order_id,goods_id,state'),
}

def snapshot(project):
    selects=[]
    for label,(table,columns) in TABLES.items():
        fields=','.join("'"+col+"',"+col for col in columns.split(','))
        selects.append(f"SELECT JSON_OBJECT('section','{label}','row',JSON_OBJECT({fields})) FROM {table};")
    selects.append("SELECT JSON_OBJECT('section','orderSnapshots','row',JSON_OBJECT('order_id',order_id,'snapshot_sha256',SHA2(snapshot,256),'reserve_request_sha256',SHA2(reserve_request,256))) FROM zj_market_b06.b_market_order;")
    result={key:[] for key in [*TABLES,'orderSnapshots']}
    for row in sql(project,' '.join(selects)):result[row['section']].append(row['row'])
    for rows in result.values():rows.sort(key=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False))
    return result

def digests(snapshot):return {key:hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode()).hexdigest().upper() for key,rows in snapshot.items()}

def environment():
    def run(args):
        result=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
        if result.returncode:raise RuntimeError('Read-only readiness/isolation check failed')
        return result.stdout
    stable=json.loads(run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(STABLE/'scripts/stable.ps1'),'-Action','ready']))
    ux=run(['py','-B',str(ROOT/'scripts/b06-deployment.py'),'ready'])
    isolation=json.loads(run(['py','-B',str(ROOT/'scripts/ux05-isolation.py')]))
    assert stable['status']=='READY' and 'UX_GATE_OPEN' in ux and isolation['status']=='PASS'
    return {'status':'PASS','stable':stable,'uxGate':'UX_GATE_OPEN','isolation':isolation}

def ownership():
    # Only explicit fixture mappings from known MAIN batches can establish ownership.
    files=[]
    old=Path('D:/Java/zj-market-b-06/.local/b06')
    files.extend(old.glob('browser/*/fixture.json'))
    files.extend(old.glob('faults/*/fixture.json'))
    files.append(Path('D:/Java/zj-market/target/team-discovery/td06_3_main_20261016_01/browser/fixture.json'))
    files.extend((ROOT/'.local/ux05').glob('*-main/fixture.json'))
    mapping={}
    for file in sorted(files):
        if not file.is_file():continue
        value=json.loads(file.read_text(encoding='utf-8-sig'))
        for purpose,goods in value.get('goods',{}).items():
            if not isinstance(goods,str) or not re.fullmatch(r'[a-f0-9-]{36}',goods):continue
            mapping.setdefault(goods,[]).append({'path':str(file),'sha256':sha(file),'batch':file.parent.name,'scenario':purpose,'environment':'main','evidence':'explicit-fixture-goods-map'})
    receipt=json.loads((STABLE/'state/adoption.json').read_text(encoding='utf-8-sig'))
    private=STABLE/'private'/receipt['release']
    manifest=json.loads((private/'files-manifest.json').read_text(encoding='utf-8'))
    seed=private/manifest['probe']['seed-goods-id.txt']['relativePath']
    seed_id=seed.read_text(encoding='utf-8').strip()
    return mapping,{'goodsId':seed_id,'path':str(seed),'sha256':sha(seed),'role':'active-stable-readiness-probe'}

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['capture','verify']);p.add_argument('--batch',required=True);a=p.parse_args()
    if ROOT.name!='zj-market-ux' or not re.fullmatch(r'cat01-1-[0-9]{8}-[0-9]{2}',a.batch):raise RuntimeError('Owned inventory root and batch required')
    work=ROOT/'.local/cat'/a.batch/'main';work.mkdir(parents=True,exist_ok=True)
    if a.action=='capture':
        if (work/'before.json').exists():raise RuntimeError('Preserve original batch; choose a new read-only observation batch')
        write(work/'environment.json',environment())
        data={project:snapshot(project) for project in ['zj-market-b06','zj-market-ux']}
        mapping,seed=ownership()
        write(work/'before.json',data);write(work/'ownership.json',{'products':mapping,'seed':seed})
        print('CAT01_CAPTURE_PASS mainProducts='+str(len(data['zj-market-b06']['products'])))
    else:
        before=json.loads((work/'before.json').read_text(encoding='utf-8'))
        observed=environment()
        initial=json.loads((work/'environment.json').read_text(encoding='utf-8'))
        assert initial['isolation']['containerIds']==observed['isolation']['containerIds'],'Container identities changed during observation'
        write(work/'environment.json',observed)
        after={project:snapshot(project) for project in before}
        write(work/'after.json',after)
        checks={project:{'before':digests(before[project]),'after':digests(after[project])} for project in before}
        assert all(x['before']==x['after'] for x in checks.values()),'Business facts changed during observation; inspect before claiming unchanged'
        write(work/'read-only-proof.json',{'status':'PASS','transactionsReadOnly':True,'identityLoginExcluded':True,'businessResourceWrites':0,'checks':checks,'capturedAt':datetime.now(timezone.utc).isoformat()})
        print('CAT01_READ_ONLY_PROOF_PASS both-environments/business-and-order-snapshots-unchanged')

if __name__=='__main__':main()
