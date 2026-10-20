"""MAIN-only owned CAT05 activities; inserts only, never updates existing activity or transaction facts."""
from pathlib import Path
import json,re,subprocess,os
ROOT=Path(__file__).resolve().parents[1];BATCH=os.environ.get('CAT_ACCEPTANCE_BATCH','cat01-5-20261020-01');WORK=ROOT/'.local/cat'/BATCH;DOCKER=['docker','--context','desktop-linux']
if not re.fullmatch(r'cat01-5-[0-9]{8}-[0-9]{2}',BATCH):raise RuntimeError('Explicit CAT05 batch required')
if ROOT.name!='zj-market-ux':raise RuntimeError('UX-only tools')
def read():
    f=json.loads((WORK/'fixture.json').read_text(encoding='utf-8'))
    assert f['batch']==BATCH and f['project']=='zj-market-b06' and f['origin']=='https://zj-market.test'
    return f
def save(f):(WORK/'fixture.json').write_text(json.dumps(f,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sql(statement):
    r=subprocess.run(DOCKER+['exec','-i','zj-market-b06-mysql-1','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names'],input=statement,capture_output=True,text=True,encoding='utf-8',timeout=90)
    if r.returncode:raise RuntimeError('Owned A configuration failed; no original data reset')
    return r.stdout.strip()
def configure():
    f=read()
    assert len(f['items'])==7 and all(x.get('goodsId') and (x['stock']=='0' or x.get('stockConfirmed')) and x['purpose']=='ACCEPTANCE' for x in f['items'])
    assert len({x['goodsId'] for x in f['items']})==7
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
            sql(f"USE group_buy_market_b06; START TRANSACTION; INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) VALUES ('{discount}','CAT05 owned acceptance','Ten yuan reduction',0,'ZJ','10'); INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time) VALUES ({activity},'CAT05 owned acceptance','{discount}',1,10,2,{minutes},1,UTC_TIMESTAMP()-INTERVAL 1 HOUR,UTC_TIMESTAMP()+INTERVAL 30 DAY); INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES ('b06','web',{activity},'{goods}'); COMMIT;")
        item['activityConfigured']=True;save(f)
    print('CAT05_OWNED_ACTIVITIES_CONFIGURED 6/new-only/no-historic-updates')
if __name__=='__main__':configure()
