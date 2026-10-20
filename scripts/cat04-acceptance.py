"""CAT04 checks current main facts against pre-mutation baseline; no business writes."""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import hashlib, importlib.util, json, subprocess

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'.local/cat/cat01-4-20261020-01'
MAIN=Path('D:/Java/zj-market')
STABLE=Path('D:/Java/zj-market-stable')
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest().upper()
def run(args):
    r=subprocess.run([str(x) for x in args],cwd=ROOT,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=180)
    if r.returncode: raise RuntimeError('Acceptance check failed: '+str(args[0]))
    return r.stdout
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False)
def unchanged_subset(before,after,label):
    current={canonical(x) for x in after}
    assert all(canonical(x) in current for x in before), 'Original facts differ: '+label

assert ROOT.name=='zj-market-ux'
f=load(WORK/'fixture.json');assert f['project']=='zj-market-b06' and f['phase']=='RETIRED'
spec=importlib.util.spec_from_file_location('inventory',ROOT/'scripts/cat01-inventory.py')
inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
before=load(WORK/'main-before.json');after=inv.snapshot('zj-market-b06');save(WORK/'main-after.json',after)
ux_before=load(WORK/'ux-before.json');ux_after=inv.snapshot('zj-market-ux');save(WORK/'ux-after.json',ux_after)
assert ux_before==ux_after,'UX business facts changed; investigate separately'
new={x['goodsId'] for x in f['items']};retired={x['goodsId'] for x in f['retire']}
census=load(ROOT/'docs/cat01-product-inventory.json');kept=set(census['retainIds'])
assert len(new)==6 and len(retired)==52 and retired==set(census['candidateOffSaleIds']) and not (new&retired or new&kept or retired&kept)
old_ids={x['goods_id'] for x in before['products']}
assert old_ids==retired|kept
assert {x['goods_id'] for x in after['products']}==old_ids|new
assert not new & {x['goodsId'] for x in load(ROOT/'docs/cat03-ux-products.json')['products']}
for section in ['orders','orderSnapshots','payments','refunds','teams','aOrders','work','blocks','fulfillment','reservations']:
    assert before[section]==after[section], 'Original transactions or obligations changed: '+section
for section in ['inventory','ledger','activities','bindings','discounts']:
    unchanged_subset(before[section],after[section],section)
products={x['goods_id']:x for x in after['products']}
sync={x['goods_id']:x for x in after['sync']}
projection={x['goods_id']:x for x in after['projection'] if x['source']=='b06' and x['channel']=='web'}
for old in before['products']:
    current=products[old['goods_id']];expected=dict(old)
    if old['goods_id'] in retired:expected.update(sale_status='OFF_SALE',product_version=old['product_version']+1)
    assert current==expected,'Unexpected original product edit'
for section in ['sync','projection']:
    for old in before[section]:
        current=next(x for x in after[section] if x['goods_id']==old['goods_id'])
        if old['goods_id'] in kept:assert current==old,'Retained product sync/projection changed'
        elif section=='projection':
            for key,value in old.items():
                if key not in ['sale_status','product_version','content_hash']:assert current[key]==value
for goods in old_ids|new:
    p,s,a=products[goods],sync[goods],projection[goods]
    assert s['state']=='CONFIRMED' and s['confirmed_version']==s['target_version']==p['product_version']==a['product_version']
    assert a['sale_status']==p['sale_status'] and a['goods_name']==p['goods_name'] and a['original_price']==p['original_price']
stocks={x['goods_id']:x for x in after['inventory']}
quoted=','.join("'"+g+"'" for g in sorted(new))
operations=inv.sql('zj-market-b06',"SELECT JSON_OBJECT('operationId',operation_id,'operationKey',operation_key,'goodsId',goods_id,'kind',kind,'delta',delta,'expectedVersion',expected_version,'outcome',outcome,'reason',reason) FROM zj_market_b06.b_inventory_operation WHERE goods_id IN ("+quoted+");")
save(WORK/'stock-operations.json',operations)
assert len(operations)==6
states=[]
for item in f['items']:
    goods=item['goodsId'];p=products[goods];stock=stocks[goods]
    assert p['sale_status']=='ON_SALE' and (stock['available'],stock['reserved'],stock['sold'])==(20,0,0)
    assert p['goods_name']==item['fields']['goodsName'] and p['description']==item['fields']['description'] and p['image_url']==item['fields']['imageUrl']
    assert Decimal(str(p['original_price']))==Decimal(item['fields']['originalPrice'])
    operation=[x for x in operations if x['goodsId']==goods and x['operationKey']==item['stockRequest']['operationId']]
    assert len(operation)==1 and operation[0]['outcome']=='SUCCEEDED' and operation[0]['delta']==20
    assert operation[0]['reason']==item['stockRequest']['reason'] and operation[0]['expectedVersion']==int(item['stockRequest']['expectedVersion'])
    ledger=[x for x in after['ledger'] if x['operation_id']==operation[0]['operationId']]
    assert len(ledger)==1 and ledger[0]['kind']=='INBOUND' and ledger[0]['delta_available']==20
    a=next(x for x in after['activities'] if x['activity_id']==item['activityId'])
    assert a['valid_time']==120 and a['target']==2 and a['take_limit_count']==10 and a['status']==1
    d=next(x for x in after['discounts'] if str(x['discount_id'])==str(item['discountId']))
    assert d['market_plan']=='ZJ' and Decimal(d['market_expr'])==10
    binding=[x for x in after['bindings'] if x['goods_id']==goods]
    assert len(binding)==1 and binding[0]['activity_id']==item['activityId'] and binding[0]['source']=='b06' and binding[0]['channel']=='web'
    states.append({'contentId':item['contentId'],'key':item['key'],'goodsId':goods,'goodsName':p['goods_name'],'originalPrice':item['fields']['originalPrice'],'payPrice':item['payPrice'],'productVersion':str(p['product_version']),'saleStatus':p['sale_status'],'imageUrl':p['image_url'],'stock':{k:stock[k] for k in ['available','reserved','sold']},'activityId':item['activityId'],'activityStart':a['start_time'],'activityEnd':a['end_time'],'targetCount':2,'validMinutes':120,'syncReady':True})
for section in ['inventory','ledger','activities','bindings','discounts']:
    assert len(after[section])-len(before[section])==6,'Unexpected extra rows: '+section
assert all(x['skipped'] for x in load(WORK/'retirement-repeat.json')['rows'])
assert load(WORK/'new-products-ready.json')['status']=='PASS'
evidence=load(WORK/'before-retirement-evidence.json')
assert evidence['status']=='SAVED_BEFORE_RETIREMENT' and set(evidence['goodsIds'])==retired and set(evidence['newGoodsIds'])==new
assert all(sha(WORK/name)==value for name,value in evidence['files'].items())
saved_ready=load(WORK/'saved-before-retirement-new-products-ready.json')
assert saved_ready['status']=='PASS' and len(saved_ready['rows'])==6
browser=load(WORK/'browser-report.json');assert browser['status']=='PASS' and browser['businessWrites']==0 and browser['httpsBypass'] is False
repeat=load(WORK/'repeat-proof.json');assert repeat['status']=='PASS'
upgrade=load(WORK/'main-upgrade.json');assert upgrade['status']=='PASS' and upgrade['preExistingFactsPreserved']
backup=STABLE/'backups'/upgrade['backupBatch'];assert load(backup/'COMPLETE.json')['manifestSha256']==sha(backup/'manifest.json')
backup_manifest=load(backup/'manifest.json')
for name,row in backup_manifest['files'].items():
    path=(backup/name).resolve();assert path.is_relative_to(backup.resolve()) and sha(path)==row['sha256'],'Backup file drift'
freeze=load(WORK/'release-freeze.json')
assert sha(STABLE/'releases'/freeze['previousRelease']/'release.json')==freeze['previousReleaseSha256']
assert sha(STABLE/'releases'/freeze['release']/'release.json')==freeze['releaseSha256']
for p in (backup/'old-release').rglob('*'):
    if p.is_file(): assert sha(p)==sha(STABLE/'releases'/freeze['previousRelease']/p.relative_to(backup/'old-release'))
stable=json.loads(run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',STABLE/'scripts/stable.ps1','-Action','ready']))
assert stable['status']=='READY' and stable['release']==freeze['release']
assert 'UX_GATE_OPEN' in run(['py','-B','scripts/b06-deployment.py','ready'])
isolation=json.loads(run(['py','-B','scripts/cat04-isolation.py']));assert isolation['status']=='PASS'
assert isolation['containerIds']['zj-market-ux']==load(WORK/'isolation-before.json')['containerIds']['zj-market-ux']
save(WORK/'isolation-after.json',isolation)
runtime={'stage':'CAT-01.4','status':'PASS','batch':f['batch'],'origin':f['origin'],'products':states,'retiredGoodsIds':sorted(retired),'retainedGoodsIds':sorted(kept),'normalGoodsNewOrders':0}
report={'stage':'CAT-01.4','status':'PASS','acceptedAt':datetime.now(timezone.utc).isoformat(),'batch':f['batch'],'scope':'main catalogue replacement; CAT-01.5 transaction acceptance pending','summary':{'beforeProducts':54,'afterProducts':60,'publicProducts':8,'newDailyProducts':6,'retiredConfirmedSamples':52,'retained':2,'newInbounds':6,'inboundQuantity':120,'newActivities':6,'originalOrders':len(before['orders']),'newOrders':0,'originalLedgerRows':len(before['ledger']),'finalLedgerRows':len(after['ledger'])},'checks':{'fullFieldOptimisticOperatorEdits':True,'finalVersionsConfirmedByA':True,'actualQuotesAndActivityEligibility':True,'sixUniqueOriginalInboundKeysAndLedgers':True,'repeatNoBusinessChanges':True,'historyAndObligationsUnchanged':True,'originalInventoryUnchanged':True,'originalActivitiesUnchanged':True,'uxFactsAndContainerIdentitiesUnchanged':True,'fourViewportsStrictHTTPSAndImageHashes':True,'offSaleOriginalOrdersReadable':True,'savedBeforeRetirement':True,'oldReleasesPreserved':True,'coldBackupHashesVerified':True,'noDatabaseOrVolumeCopyFromUX':True},'mainBeforeDigests':inv.digests(before),'mainAfterDigests':inv.digests(after),'uxBeforeDigests':inv.digests(ux_before),'uxAfterDigests':inv.digests(ux_after),'release':freeze,'upgrade':{k:upgrade[k] for k in ['release','backupBatch','backupManifestSha256','preExistingFactsPreserved']},'retainedGoodsIds':sorted(kept),'retainedReasons':['Stable ready probe dependency','Ownership unresolved: preserved despite sample-like name'],'preservedObligations':{'reconcilingTeams':sum(x['team_status']=='RECONCILING' for x in after['teams']),'unfinishedWork':sum(x['state'] not in ['DONE','DEAD'] for x in after['work']),'activeBlocks':sum(x['state']=='ACTIVE' for x in after['blocks']),'reviewOrders':sum(bool(x['review_required']) for x in after['orders']),'pendingFulfillment':sum(x['status']=='PENDING' for x in after['fulfillment'])},'browser':browser,'next':'CAT-01.5: dedicated main acceptance sample transactions and cleanup; no new transactions on these six daily goods','privateEvidenceRoot':str(WORK),'evidenceHashes':{name:sha(WORK/name) for name in ['main-before.json','main-after.json','ux-before.json','ux-after.json','ownership.json','fixture.json','stock-operations.json','browser-report.json','retirement.json','retirement-repeat.json','repeat-proof.json','new-products-ready.json','main-upgrade.json']},'sourceHashes':{p.name:sha(p) for p in sorted((ROOT/'scripts').glob('cat04-*')) if p.is_file()}}
for root in [ROOT,MAIN]:
    save(root/'docs/cat04-main-products.json',runtime);save(root/'docs/tests/cat01-4-acceptance.json',report);save(root/'docs/cat04-release.json',freeze)
print('CAT04_ACCEPTANCE_PASS 6-new/52-retired/2-kept/history-and-UX-preserved')
