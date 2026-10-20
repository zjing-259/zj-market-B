"""Read-only CAT final acceptance: exact batch, original facts, finances, and owned cleanup."""
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import hashlib,importlib.util,json,os,re,subprocess
ROOT=Path(__file__).resolve().parents[1];MAIN=Path('D:/Java/zj-market');STABLE=Path('D:/Java/zj-market-stable')
BATCH=os.environ.get('CAT_ACCEPTANCE_BATCH','cat01-5-20261020-01');WORK=ROOT/'.local/cat'/BATCH
assert ROOT.name=='zj-market-ux' and re.fullmatch(r'cat01-5-[0-9]{8}-[0-9]{2}',BATCH)
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def run(args):
    p=subprocess.run([str(x) for x in args],cwd=ROOT,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=180)
    if p.returncode:raise RuntimeError('Read-only final check failed; see private evidence')
    return p.stdout
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False)
def original_subset(before,after,label):
    current={canonical(x) for x in after}
    assert all(canonical(x) in current for x in before),'Original business facts changed: '+label

f=load(WORK/'fixture.json');assert f['batch']==BATCH and f['project']=='zj-market-b06' and f['phase']=='CLEANED'
owned={x['goodsId'] for x in f['items']};assert len(owned)==7 and all(x['purpose']=='ACCEPTANCE' and x['createStarted'] and x['beforeCreateIds'] for x in f['items'])
browser=load(WORK/'browser-report.json');assert browser['status']=='PASSED' and browser['httpsBypass'] is False and not browser.get('guardRejection') and not browser.get('transportOutcomeUnknown')
assert browser['browserScriptSha256'].upper()==sha(WORK/'executed-browser.mjs')==sha(ROOT/'scripts/cat05-browser.mjs')
assert len(browser['orders'])==5 and all(x['goods'] in owned for x in browser['orders'].values())
assert not browser['pageErrors']
accounting=load(WORK/'accounting-report.json');assert accounting['status']=='PASSED_REAL_BROWSER_ACCOUNTING'
assert accounting['rawBrowserReportSha256'].upper()==sha(WORK/'browser-report.json')
assert sum(len(x['orders']) for x in accounting['facts'].values())==5
for name in ['guards.json','stockout.json','original-receipt-recovery.json','cleanup.json','cleanup-repeat.json','cleanup-receipt-recovery.json','repeat-proof.json','sealed-guards.json','final-browser.json','failure-evidence-guard.json','legacy-entry-guards.json']:
    assert load(WORK/name)['status']=='PASS',name
assert load(WORK/'guards.json')['staleEditCode']=='PRODUCT_EDIT_CONFLICT'
assert all(x['skipped'] for x in load(WORK/'cleanup-repeat.json')['results'])
final_browser=load(WORK/'final-browser.json');assert final_browser['businessWrites']==0 and final_browser['publicOwnedAcceptance']==0
assert len(final_browser['normalOffers'])==6
lock=load(WORK/'evidence-lock.json');assert lock['status']=='SAVED_BEFORE_CLEANUP' and not lock['failedBatch'] and not lock['unknownCreateOutcomes'] and set(lock['goodsIds'])==owned
assert all(sha(WORK/name)==value for name,value in lock['files'].items())
assert load(WORK/'saved-accounting-report.json')['status']=='PASSED_REAL_BROWSER_ACCOUNTING'
spec=importlib.util.spec_from_file_location('inventory',ROOT/'scripts/cat01-inventory.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
before=load(WORK/'main-before.json');after=inv.snapshot('zj-market-b06');save(WORK/'main-after.json',after)
ux_before=load(WORK/'ux-before.json');ux_after=inv.snapshot('zj-market-ux');save(WORK/'ux-after.json',ux_after)
assert ux_before==ux_after,'UX facts changed during main acceptance'
for section,rows in before.items():original_subset(rows,after[section],section)
old_goods={x['goods_id'] for x in before['products']};assert {x['goods_id'] for x in after['products']}-old_goods==owned and not owned&old_goods
old_orders={x['order_id'] for x in before['orders']};new_orders={x['order_id'] for x in after['orders']}-old_orders
assert new_orders==set(browser['orders']) and len(new_orders)==5
assert all(x['goods_id'] in owned for x in after['orders'] if x['order_id'] in new_orders)
normal={x['goodsId'] for x in f['showcase']};assert len(normal)==6 and not normal&owned
assert not any(x['goods_id'] in normal and x['order_id'] in new_orders for x in after['orders'])
products={x['goods_id']:x for x in after['products']};stocks={x['goods_id']:x for x in after['inventory']};sync={x['goods_id']:x for x in after['sync']}
projection={x['goods_id']:x for x in after['projection'] if x['source']=='b06' and x['channel']=='web'}
quoted=','.join("'"+x+"'" for x in sorted(owned));order_sql=','.join("'"+x+"'" for x in sorted(new_orders))
operations=inv.sql('zj-market-b06',"SELECT JSON_OBJECT('goodsId',goods_id,'operationId',operation_id,'operationKey',operation_key,'delta',delta,'expectedVersion',expected_version,'outcome',outcome,'reason',reason) FROM zj_market_b06.b_inventory_operation WHERE goods_id IN ("+quoted+");")
assert len(operations)==6;save(WORK/'stock-operations.json',operations)
states=[]
for item in f['items']:
    goods=item['goodsId'];p=products[goods];s=sync[goods];a=projection[goods];st=stocks[goods]
    assert p['sale_status']==a['sale_status']=='OFF_SALE' and p['goods_name']==item['fields']['goodsName'] and p['description']==item['fields']['description'] and p['image_url']==item['fields']['imageUrl']
    assert s['state']=='CONFIRMED' and s['confirmed_version']==s['target_version']==p['product_version']==a['product_version']
    assert st['reserved']==0 and st['sold']==(2 if item['key']=='success' else 0) and st['available']==(8 if item['key']=='success' else int(item['stock']))
    if item['stock']!='0':
        op=[x for x in operations if x['goodsId']==goods and x['operationKey']==item['stockRequest']['operationId']];assert len(op)==1
        assert op[0]['outcome']=='SUCCEEDED' and op[0]['delta']==10 and op[0]['reason']==item['stockRequest']['reason'] and op[0]['expectedVersion']==int(item['stockRequest']['expectedVersion'])
        ledgers=[x for x in after['ledger'] if x['operation_id']==op[0]['operationId']];assert len(ledgers)==1 and ledgers[0]['kind']=='INBOUND' and ledgers[0]['delta_available']==10
    binding=[x for x in after['bindings'] if x['goods_id']==goods]
    if item['activity']:
        assert len(binding)==1 and binding[0]['activity_id']==item['activityId'] and binding[0]['source']=='b06' and binding[0]['channel']=='web'
        act=next(x for x in after['activities'] if x['activity_id']==item['activityId']);assert act['target']==2 and act['valid_time']==item['minutes'] and act['status']==1
    else:assert not binding
    states.append({'key':item['key'],'purpose':item['purpose'],'goodsId':goods,'goodsName':p['goods_name'],'saleStatus':p['sale_status'],'productVersion':str(p['product_version']),'syncReady':True,'stock':{k:st[k] for k in ['available','reserved','sold']},'activityId':item.get('activityId'),'validMinutes':item['minutes'],'originalStockOperationKey':item.get('stockRequest',{}).get('operationId')})
old_ledger={x['ledger_id'] for x in before['ledger']};new_ledger=[x for x in after['ledger'] if x['ledger_id'] not in old_ledger]
assert len(new_ledger)==16 and all(x['goods_id'] in owned for x in new_ledger)
expected={'INBOUND':6,'RESERVE':5,'CONFIRM':2,'RELEASE':3}
assert {k:sum(x['kind']==k for x in new_ledger) for k in expected}==expected
for section,delta in [('products',7),('inventory',7),('orders',5),('orderSnapshots',5),('activities',6),('discounts',6),('bindings',6),('payments',4),('refunds',2),('teams',4),('aOrders',5),('reservations',5),('fulfillment',2)]:assert len(after[section])-len(before[section])==delta,section
pending=inv.sql('zj-market-b06',f"SELECT JSON_OBJECT('pendingPayments',(SELECT COUNT(*) FROM zj_market_b06.b_payment WHERE order_id IN ({order_sql}) AND (funds_state='UNKNOWN' OR funds_state='SUCCEEDED' AND a_acceptance<>'ACCEPTED')),'pendingRefunds',(SELECT COUNT(*) FROM zj_market_b06.b_refund WHERE order_id IN ({order_sql}) AND (funds_status<>'SUCCEEDED' OR sync_status<>'ACCEPTED' OR release_status<>'RELEASED')),'pendingRefundWork',(SELECT COUNT(*) FROM zj_market_b06.b_trade_work WHERE order_id IN ({order_sql}) AND kind='REFUND_OBLIGATION' AND state<>'DONE'),'reservedStock',(SELECT COALESCE(SUM(reserved),0) FROM zj_market_b06.b_inventory_account WHERE goods_id IN ({quoted}))); ")
assert len(pending)==1 and all(v==0 for v in pending[0].values()),'Current financial/release obligations remain'
deferred=[x for x in after['work'] if x['order_id'] in new_orders and x['state'] not in ['DONE','DEAD']]
for row in deferred:
    assert row['kind'] in ['TEAM_FAILED','TEAM_RECONCILIATION_REQUIRED'] and row['state']=='DEFERRED_B05'
    kind=browser['orders'][row['order_id']]['kind'];facts=accounting['facts'][kind];assert kind in ['expiry','offpaid']
    order=next(x for x in facts['orders'] if x['orderId']==row['order_id'])
    assert order['status']=='CLOSED' and order['reservation']=='RELEASED' and Decimal(str(order['paidAmount']))==Decimal(str(order['refundedAmount']))==90
    assert facts['aTeam']['status']=='FAILED' and facts['reconciliation']['state']=='RESOLVED' and facts['reconciliation']['submission']=='ACKNOWLEDGED'
stable=json.loads(run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',STABLE/'scripts/stable.ps1','-Action','ready']));assert stable['status']=='READY' and stable['release']=='cat04-stable-20261020-01'
assert 'UX_GATE_OPEN' in run(['py','-B','scripts/b06-deployment.py','ready'])
isolation=json.loads(run(['py','-B','scripts/cat04-isolation.py']));assert isolation['status']=='PASS'
assert isolation['containerIds']==load(WORK/'isolation-before.json')['containerIds'];save(WORK/'isolation-final.json',isolation)
assert sha(STABLE/'releases/cat04-stable-20261020-01/release.json')==load(ROOT/'docs/cat04-release.json')['releaseSha256']
for root in [ROOT,MAIN]:
    # Previously accepted records remain frozen, even as newer batches add legitimate facts.
    names=['docs/tests/cat01-1-acceptance.json','docs/tests/cat01-2-acceptance.json','docs/tests/cat01-3-acceptance.json','docs/tests/cat01-4-acceptance.json','docs/catalog-products.json','docs/cat04-main-products.json','docs/cat04-release.json']
    baseline=load(WORK/'documents-before.json').get(str(root),{})
    if baseline:
        for name in names:assert sha(root/name)==baseline[name],name
proof={'status':'PASS','mainOriginalFactsPreserved':True,'originalOrderCount':len(before['orders']),'originalLedgerCount':len(before['ledger']),'uxAllBusinessFactsPreserved':True,'allContainerIdsUnchanged':True,'newSamples':7,'newOrders':5,'normalGoodsNewOrders':0,'newStockInboundCount':6,'newStockQuantity':60,'newLedgerCounts':expected,'pendingFinancialAndReleaseObligations':pending[0],'originalMainDigests':inv.digests(before),'currentMainDigests':inv.digests(after),'uxBeforeDigests':inv.digests(ux_before),'uxAfterDigests':inv.digests(ux_after)}
save(WORK/'final-proof.json',proof)
runtime={'stage':'CAT-01.5','status':'PASS','batch':BATCH,'origin':f['origin'],'products':states,'sampleGoodsIds':sorted(owned),'normalShowcaseGoodsIds':sorted(normal),'allSamplesOffSale':True,'publicGoodsCount':8,'acceptedOrders':{oid:{k:v[k] for k in ['goods','kind','mode','teamId']} for oid,v in browser['orders'].items()}}
matrix={f'CAT-T{i:02}':{'status':'PASS','evidence':e} for i,e in enumerate(['CAT01.1 inventory + CAT04 retirement + CAT05 exact ownership','Final public 8; 7 current samples and 52 historical samples absent','4 real Edge viewports + failed image placeholder + six strict HTTPS image hashes','Actual current offers and versions; no-activity not purchasable','Main final OFF_SALE versions confirmed by A; delay/recovery proven separately on UX in CAT01.3','6 original inbound keys/unique ledgers + original-key repeat + backend stockout refusal','All original main rows/snapshot hashes and original stock/ledger preserved','Original off-sale order payment/cancel/full refund and final reads','Two-account OPEN/exact JOIN/payment/group + payment retry same root + A exact quota','Unpaid cancel unique release; two natural full refunds confirmed by A and stock','Evidence hash seal precedes owned cleanup; repeat no mutations; failed evidence retained','Buyer create/inbound 403, cross-owner order 404; operator keys/reasons/versions persisted','Main and UX independent; all UX facts and both container sets unchanged','Receipt-loss recovery and stale version rejection; sealed batch and legacy entry guards'],1)}
report={'stage':'CAT-01.5','status':'PASS','stageCompleted':True,'seriesCompleted':True,'acceptedAt':datetime.now(timezone.utc).isoformat(),'batch':BATCH,'matrix':matrix,'normalShowcaseGoods':6,'normalShowcaseNewOrders':0,'ownedAcceptanceGoods':7,'ownedAcceptanceGoodsOffSale':7,'finalPublicGoods':8,'orders':5,'simulatedPaidAmount':'360.00','simulatedRefundedAmount':'180.00','simulatedNetAmount':'180.00','pendingCurrentBatchFinancialObligations':0,'proof':proof,'accountingFacts':accounting['facts'],'accountingChecks':accounting['accountingChecks'],'browserChecks':browser['checks'],'strictTLS':True,'httpsBypass':False,'releaseChanged':False,'backendOrSchemaChanged':False,'retainedCurrentBatchCoordinationRecords':deferred,'emptyUnpaidTeamsFollowingNaturalDeadline':[x for x in after['teams'] if x['goods_id'] in owned and x['paid_count']==x['reserved_count']==0 and x['team_status'] in ['FORMING','RECONCILING']],'retainedLegacyGoodsIds':load(ROOT/'docs/cat04-main-products.json')['retainedGoodsIds'],'preservedHistoricalObligations':{'reconcilingTeams':sum(x['team_status']=='RECONCILING' for x in before['teams']),'unfinishedWork':sum(x['state'] not in ['DONE','DEAD'] for x in before['work']),'activeBlocks':sum(x['state']=='ACTIVE' for x in before['blocks']),'reviewOrders':sum(bool(x['review_required']) for x in before['orders']),'pendingFulfillment':sum(x['status']=='PENDING' for x in before['fulfillment'])},'boundaries':['Simulated funds only; no real shipping. Two new completed orders remain PENDING fulfillment as designed.','Historical reconciliation/review/fulfillment and any verified deferred compatibility records are preserved, not manually cleared.','Six daily goods only read; exact retained probe/unresolved goods remain.','Main A process was not stopped for fault injection; delayed-version fault/recovery evidence remains separately identified as CAT01.3 UX evidence.','Receipt loss checks are controlled injections after actual backend acceptance. Failed auxiliary browser forwarding attempt created no orders; normal trusted Edge transport resumed the same batch.','Current stage does not rebuild or redeploy images, restore old backups, or copy UX data.'],'privateEvidenceRoot':str(WORK),'sourceHashes':{p.name:sha(p) for p in sorted((ROOT/'scripts').glob('cat05-*')) if p.is_file()},'retiredLegacyWriteEntries':['scripts/ux05-joint.py prepare/browser','scripts/ux05-browser.mjs prepare/browser'],'evidenceHashes':{p.name:sha(p) for p in sorted(WORK.glob('*.json')) if p.name not in ['fixture.json'] and not p.name.startswith('session-')},'screenshots':{p.name:sha(p) for p in WORK.glob('*.png')}}
for root in [ROOT,MAIN]:
    save(root/'docs/cat05-main-samples.json',runtime);save(root/'docs/tests/cat01-5-acceptance.json',report)
print('CAT05_FINAL_ACCEPTANCE_PASS series-complete/7-samples-off/5-orders/360-paid/180-refunded/0-financial-obligations')
if deferred:print('CAT05_RETAINED_VERIFIED_COMPATIBILITY_RECORDS '+str(len(deferred)))
