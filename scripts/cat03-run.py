"""Explicit UX-only CAT preparation/configuration and isolated A delay drill."""
from pathlib import Path
import argparse,importlib.util,json,re,subprocess,time
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'.local/cat/cat01-3-20261020-01';DOCKER=['docker','--context','desktop-linux']
if ROOT.name!='zj-market-ux':raise RuntimeError('UX-only tools')
def read():
    f=json.loads((WORK/'fixture.json').read_text(encoding='utf-8'))
    assert f['project']=='zj-market-ux' and f['origin']=='https://zj-market-ux.test:8446'
    return f
def save(f):(WORK/'fixture.json').write_text(json.dumps(f,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sql(statement):
    r=subprocess.run(DOCKER+['exec','-i','zj-market-ux-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names'],input=statement,capture_output=True,text=True,encoding='utf-8',timeout=90)
    if r.returncode:raise RuntimeError('Owned A configuration failed; no original data reset')
    return r.stdout.strip()
def node(action):subprocess.run(['node','scripts/cat03-products.mjs',action],cwd=ROOT,check=True)
def configure():
    f=read()
    if not all(x.get('activityId') for x in f['items'] if x['activity']):
        base=int(sql('SELECT GREATEST(700000,COALESCE(MAX(activity_id),0))+1 FROM group_buy_market_b06.group_buy_activity;'))
        for i,item in enumerate(f['items']):
            if item['activity']:item.update(activityId=base+i,discountId=(base+i)*100+1)
        save(f)
    for item in f['items']:
        if not item['activity']:continue
        goods=item['goodsId'];assert re.fullmatch('[a-f0-9-]{36}',goods)
        activity,discount,minutes=int(item['activityId']),int(item['discountId']),int(item['minutes'])
        existing=sql(f"SELECT a.activity_id,a.discount_id,a.valid_time,a.target,a.take_limit_count,a.status,d.market_plan,d.market_expr,s.goods_id,s.source,s.channel FROM group_buy_market_b06.group_buy_activity a JOIN group_buy_market_b06.group_buy_discount d ON d.discount_id=a.discount_id JOIN group_buy_market_b06.sc_sku_activity s ON s.activity_id=a.activity_id WHERE a.activity_id={activity};")
        expected=f'{activity}\t{discount}\t{minutes}\t2\t10\t1\tZJ\t10\t{goods}\tb06\tweb'
        if existing:
            if existing!=expected:raise RuntimeError('Existing config differs; refusing overwrite')
        else:
            sql(f"USE group_buy_market_b06; START TRANSACTION; INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) VALUES ('{discount}','CAT UX owned','Ten yuan reduction',0,'ZJ','10'); INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time) VALUES ({activity},'CAT UX owned','{discount}',1,10,2,{minutes},1,UTC_TIMESTAMP()-INTERVAL 1 HOUR,UTC_TIMESTAMP()+INTERVAL 30 DAY); INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES ('b06','web',{activity},'{goods}'); COMMIT;")
        item['activityConfigured']=True;save(f)
    print('CAT03_OWNED_ACTIVITIES_CONFIGURED 13/new-only/no-historic-updates')
def sync_drill():
    assert all(x['fields']['saleStatus']=='ON_SALE' for x in read()['items'])
    try:
        subprocess.run(DOCKER+['stop','zj-market-ux-marketing-a-1'],check=True,capture_output=True)
        node('pending-update')
    finally:
        subprocess.run(DOCKER+['start','zj-market-ux-marketing-a-1'],check=True,capture_output=True)
        end=time.time()+150
        while time.time()<end:
            status=subprocess.check_output(DOCKER+['inspect','--format','{{.State.Health.Status}}','zj-market-ux-marketing-a-1'],text=True).strip()
            if status=='healthy':break
            time.sleep(2)
        else:raise RuntimeError('Owned A did not recover')
    node('verify');print('CAT03_A_SYNC_DELAY_DRILL_PASS restored-healthy')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['configure','sync-drill']);a=p.parse_args()
    configure() if a.action=='configure' else sync_drill()
