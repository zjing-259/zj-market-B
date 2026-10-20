"""Finalize CAT-01.3 only after owned cleanup, original-fact and isolation checks."""
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import importlib.util,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'.local/cat/cat01-3-20261020-01'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as file:
        for block in iter(lambda:file.read(1024*1024),b''):h.update(block)
    return h.hexdigest().upper()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def run(args):
    r=subprocess.run([str(x) for x in args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    if r.returncode:raise RuntimeError('Final verification failed; details retained in private batch')
    return r.stdout
assert ROOT.name=='zj-market-ux'
fixture=load(WORK/'fixture.json');assert fixture['project']=='zj-market-ux' and fixture['phase']=='CLEANED'
browser=load(WORK/'browser-report.json');assert browser['status']=='PASSED' and browser['httpsBypass'] is False
assert browser['browserScriptSha256'].upper()==sha(WORK/'executed-browser.mjs')==sha(ROOT/'scripts/cat03-browser.mjs')
final_browser=load(WORK/'final-browser.json');assert final_browser['status']=='PASS' and final_browser['businessWrites']==0 and final_browser['publicOwnedAcceptance']==0
for file in ['guards.json','sync-delay.json','repeat-preparation.json','cleanup.json','cleanup-repeat.json','cleanup-loss-test.json','sealed-republish-guard.json']:
    assert load(WORK/file)['status']=='PASS',file
assert all(x['skipped'] for x in load(WORK/'cleanup-repeat.json')['results'])
assert fixture['stockoutCheck']['status']=='PASS'
success=next(x for x in fixture['items'] if x['key']=='success')
assert success['recoveredCreate'] and success['stockOutcomeUnknown'] and success['stockConfirmed'] and success['recoveredEdit']
lock=load(WORK/'evidence-lock.json');assert lock['status']=='SAVED_BEFORE_CLEANUP' and not lock['failedBatch']
assert all(sha(WORK/name)==expected for name,expected in lock['files'].items())
assert lock['goodsIds']==[x['goodsId'] for x in fixture['items'] if x['purpose']=='ACCEPTANCE']
accounting=load(WORK/'accounting-report.json');assert accounting['status']=='PASSED_REAL_BROWSER_ACCOUNTING'
assert sum(len(x['orders']) for x in accounting['facts'].values())==5
regression=load(WORK/'regression.json');assert len(regression)==4 and all(x['exitCode']==0 for x in regression)
spec=importlib.util.spec_from_file_location('cat_inventory',ROOT/'scripts/cat01-inventory.py');inventory=importlib.util.module_from_spec(spec);spec.loader.exec_module(inventory)
main_before=load(WORK/'main-before.json');main_after=inventory.snapshot('zj-market-b06')
assert main_before==main_after,'Main business facts changed; do not claim untouched'
save(WORK/'main-after.json',main_after)
ux_before=load(WORK/'ux-before.json');ux_after=inventory.snapshot('zj-market-ux');save(WORK/'ux-after.json',ux_after)
canonical=lambda row:json.dumps(row,sort_keys=True,ensure_ascii=False)
for section,rows in ux_before.items():
    current={canonical(x) for x in ux_after[section]}
    assert all(canonical(row) in current for row in rows),'Pre-existing UX facts changed: '+section
owned={x['goodsId'] for x in fixture['items']};before_ids={x['goods_id'] for x in ux_before['products']}
assert {x['goods_id'] for x in ux_after['products']}-before_ids==owned and len(owned)==14
products={x['goods_id']:x for x in ux_after['products']};stocks={x['goods_id']:x for x in ux_after['inventory']};sync={x['goods_id']:x for x in ux_after['sync']}
projections={x['goods_id']:x for x in ux_after['projection'] if x['source']=='b06' and x['channel']=='web'}
quoted=','.join("'"+goods+"'" for goods in sorted(owned))
operations=inventory.sql('zj-market-ux',"SELECT JSON_OBJECT('operationId',operation_id,'operationKey',operation_key,'goodsId',goods_id,'kind',kind,'delta',delta,'expectedVersion',expected_version,'outcome',outcome,'reason',reason) FROM zj_market_b06.b_inventory_operation WHERE goods_id IN ("+quoted+");")
save(WORK/'stock-operations.json',operations)
states=[]
for item in fixture['items']:
    goods=item['goodsId'];p=products[goods];st=stocks[goods];s=sync[goods];projection=projections[goods]
    assert p['sale_status']==('ON_SALE' if item['purpose']=='SHOWCASE' else 'OFF_SALE')
    assert s['state']=='CONFIRMED' and s['confirmed_version']==s['target_version']==p['product_version']==projection['product_version']
    assert projection['sale_status']==p['sale_status'] and p['goods_name']==item['fields']['goodsName'] and p['description']==item['fields']['description'] and Decimal(str(p['original_price']))==Decimal(item['price'])
    if item['purpose']=='SHOWCASE':
        assert (st['available'],st['reserved'],st['sold'])==(20,0,0)
        assert not any(x['goods_id']==goods for x in ux_after['orders'])
    if 'stockRequest' in item:
        operation=[x for x in operations if x['operationKey']==item['stockRequest']['operationId'] and x['goodsId']==goods]
        assert len(operation)==1 and operation[0]['outcome']=='SUCCEEDED' and operation[0]['delta']==int(item['stock']) and operation[0]['reason']==item['stockRequest']['reason'] and operation[0]['expectedVersion']==int(item['stockRequest']['expectedVersion'])
        ledgers=[x for x in ux_after['ledger'] if x['operation_id']==operation[0]['operationId']]
        assert len(ledgers)==1 and ledgers[0]['kind']=='INBOUND' and ledgers[0]['delta_available']==int(item['stock'])
    states.append({'key':item['key'],'purpose':item['purpose'],'contentId':item.get('contentId'),'goodsId':goods,'goodsName':p['goods_name'],'productVersion':str(p['product_version']),'saleStatus':p['sale_status'],'stock':{k:st[k] for k in ['available','reserved','sold']},'activityId':item.get('activityId'),'validMinutes':item['minutes'],'payPrice':item['payPrice'],'imageUrl':p['image_url'],'syncReady':True})
assert len(ux_after['orders'])-len(ux_before['orders'])==5
old_ledger={x['ledger_id'] for x in ux_before['ledger']}
inbounds=[x for x in ux_after['ledger'] if x['ledger_id'] not in old_ledger and x['kind']=='INBOUND']
assert len(inbounds)==13 and sum(x['delta_available'] for x in inbounds)==190
old_activities={x['activity_id'] for x in ux_before['activities']}
assert len({x['activity_id'] for x in ux_after['activities']}-old_activities)==13
pending=[x for x in ux_after['work'] if x['order_id'] in browser['orders'] and x['state'] not in ['DONE','DEAD']]
for item in pending:
    # Late legacy coordination notifications can remain deferred after the
    # independent refund/reconciliation path has completely settled. Preserve
    # these records and prove their financial state; never clear them by SQL.
    assert item['kind'] in ['TEAM_FAILED','TEAM_RECONCILIATION_REQUIRED'] and item['state']=='DEFERRED_B05'
    kind=browser['orders'][item['order_id']]['kind'];facts=accounting['facts'][kind]
    order=next(x for x in facts['orders'] if x['orderId']==item['order_id'])
    assert order['status']=='CLOSED' and order['reservation']=='RELEASED' and Decimal(str(order['paidAmount']))==Decimal(str(order['refundedAmount']))==90
    assert facts['reconciliation']['state']=='RESOLVED' and facts['reconciliation']['submission']=='ACKNOWLEDGED' and facts['aTeam']['status']=='FAILED'
stable=json.loads(run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File','D:/Java/zj-market-stable/scripts/stable.ps1','-Action','ready']));assert stable['status']=='READY'
assert 'UX_GATE_OPEN' in run(['py','-B','scripts/b06-deployment.py','ready'])
isolated=json.loads(run(['py','-B','scripts/cat03-isolation.py']));assert isolated['status']=='PASS'
assert load(WORK/'environment-before.json')['isolation']['containerIds']['zj-market-b06']==isolated['containerIds']['zj-market-b06']
save(WORK/'isolation-final.json',isolated)
release=load(ROOT/'docs/cat03-web-release.json')
assets={}
for file in sorted((ROOT/'frontend/dist').rglob('*')):
    if not file.is_file():continue
    relative=str(file.relative_to(ROOT/'frontend/dist')).replace('\\','/')
    digest=run(['docker','--context','desktop-linux','exec','zj-market-ux-web-1','sha256sum','/usr/share/nginx/html/'+relative]).split()[0].upper()
    assert digest==sha(file),relative
    assets[relative]=digest
assert sha(WORK/'web-cat03-20261020-01.tar')==release['archiveSha256']
proof={'status':'PASS','mainBusinessDigestsBefore':inventory.digests(main_before),'mainBusinessDigestsAfter':inventory.digests(main_after),'mainContainerIdsUnchanged':True,'originalMainOrdersPreserved':len(main_before['orders']),'originalUXFactsPreserved':True,'newOwnedProducts':14,'newOwnedActivities':13,'newInboundLedgers':13,'initialStockAdded':190,'ownedAcceptedOrders':5,'showcaseOrders':0}
save(WORK/'final-proof.json',proof)
runtime={'stage':'CAT-01.3','origin':fixture['origin'],'status':'PASS','batch':fixture['batch'],'products':states,'sampleGoodsIds':lock['goodsIds'],'normalShowcaseGoodsIds':[x['goodsId'] for x in states if x['purpose']=='SHOWCASE'],'mainProductsCreated':0}
save(ROOT/'docs/cat03-ux-products.json',runtime)
checks=['six-normal-products-created-off-sale-then-final-version-confirmed','six-original-images-actual-HTTPS-hashes-and-four-viewports','13-stock-inbounds-original-keys-no-repeat','unknown-product-create-recovered-by-exact-fields-and-before-IDs','unknown-inbound-recovered-by-original-operation','A-product-version-and-actual-quote-confirmed','A-unavailable-unconfirmed-version-blocks-trial-and-recovers','stale-product-version-rejected','stockout-backend-rejects-with-no-valid-order','no-activity-not-purchasable-and-bad-image-placeholder','showcase-only-read-no-new-orders','two-account-open-exact-join-payment-group-completion','natural-expiry-full-refund-and-unique-stock-release','off-sale-original-payment-cancel-refund-and-read-recovery','buyer-write-permission-and-cleanup-ownership-boundaries','evidence-frozen-before-only-owned-8-samples-off-sale','off-sale-receipt-loss-recovered-no-repeat-edit','cleanup-repeat-zero-writes-and-sealed-batch-no-republish','five-orders-funds-stock-A-quota-unique-ledgers','main-business-and-container-identities-unchanged','preexisting-UX-business-facts-preserved','frontend-type-build-regressions-and-runtime-assets-match']
sources={str(file.relative_to(ROOT)).replace('\\','/'):sha(file) for file in (ROOT/'scripts').glob('cat03-*') if file.is_file()}
report={'stage':'CAT-01.3','status':'PASS','stageCompleted':True,'seriesCompleted':False,'generatedAt':datetime.now(timezone.utc).isoformat(),'batch':fixture['batch'],'checks':checks,'normalShowcaseProducts':6,'ownedAcceptanceProducts':8,'ownedAcceptanceOffSale':8,'showcaseStockEach':20,'showcaseAcceptedOrders':0,'acceptedOrders':5,'simulatedPaidAmount':'360.00','simulatedRefundedAmount':'180.00','netAmount':'180.00','accountingChecks':accounting['accountingChecks'],'accountingFacts':accounting['facts'],'mainUnchanged':proof,'strictTLS':True,'ignoreHTTPSErrors':False,'regressions':regression,'productionBuild':'PASS vue-tsc + vite','runtimeAssets':assets,'webRelease':release,'environment':{'stable':stable,'ux':'UX_GATE_OPEN','isolation':isolated['checks']},'runtimeProductsSha256':sha(ROOT/'docs/cat03-ux-products.json'),'evidenceLockSha256':sha(WORK/'evidence-lock.json'),'rawEvidenceSha256':{name:sha(WORK/name) for name in ['accounting-before-cleanup.json','accounting-report.json','browser-report.json','final-browser.json','repeat-preparation.json','cleanup.json','cleanup-repeat.json','sync-delay.json','stockout.json','guards.json','final-proof.json']},'sourceSha256':sources,'screenshots':{x.name:sha(x) for x in WORK.glob('*.png')},'boundaries':['UX-only: no main catalogue, stock, activity, order or runtime deployment change','Receipt-loss variants are controlled injections after real backend acceptance, with original identities retained','Daily products use authored demo prices/specifications and original illustrations, not real fulfillment','Only this batch of eight ACCEPTANCE goods was retired; older UX fixtures and all main samples were retained','CAT-01.4 main replacement and CAT-01.5 final main acceptance remain pending','Preexisting historical reconciliation/review/fulfillment obligations are preserved; not repaired by this stage']}
report['retainedCurrentBatchCoordinationRecords']=pending
report['pendingCurrentBatchFinancialObligations']=0
report['emptyUnpaidTeamsStillFollowingNaturalDeadline']=[x for x in ux_after['teams'] if x['team_id'] in {o['teamId'] for o in browser['orders'].values()} and x['team_status'] in ['FORMING','RECONCILING'] and x['paid_count']==x['reserved_count']==0]
report['boundaries'].append('Any listed deferred compatibility coordination record is retained with exact ID; associated refund/release and A reconciliation are independently verified complete. Empty unpaid teams may follow their natural deadline; no forced team close')
save(ROOT/'docs/tests/cat01-3-acceptance.json',report)
print('CAT03_FINAL_ACCEPTANCE_PASS six-showcase/eight-off-sale/five-orders/main-unchanged')
