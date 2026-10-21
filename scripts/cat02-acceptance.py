"""Read-only final acceptance for the two explicitly reviewed legacy goods."""
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import hashlib,importlib.util,json,subprocess
ROOT=Path(__file__).resolve().parents[1];MAIN=Path('D:/Java/zj-market');STABLE=Path('D:/Java/zj-market-stable');WORK=ROOT/'.local/cat/cat02-closeout-20261021-01'
TARGETS={'5a4d973a-4d83-4f7b-9155-4c331b436fc4','db7100d5-12ad-4b24-b7b3-dc773b0f33b8'}
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest().upper()
def run(cmd,timeout=180):
    r=subprocess.run([str(x) for x in cmd],cwd=ROOT,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=timeout)
    if r.returncode:raise RuntimeError('Acceptance subprocess failed; sanitized private evidence retained')
    return r.stdout
assert ROOT.name=='zj-market-ux'
spec=importlib.util.spec_from_file_location('inventory',ROOT/'scripts/cat01-inventory.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
before=load(WORK/'main-before.json');after=inv.snapshot('zj-market-b06');save(WORK/'main-after.json',after)
for section in before:
    if section not in ['products','sync','projection']:assert before[section]==after[section],'Original business facts changed: '+section
products={x['goods_id']:x for x in after['products']};sync={x['goods_id']:x for x in after['sync']};projection={x['goods_id']:x for x in after['projection']}
for old in before['products']:
    expected=dict(old)
    if old['goods_id'] in TARGETS:expected.update(sale_status='OFF_SALE',product_version=old['product_version']+1)
    assert expected==products[old['goods_id']],'Unexpected product edit'
for section in ['sync','projection']:
    for old in before[section]:
        current=next(x for x in after[section] if x['goods_id']==old['goods_id'])
        if old['goods_id'] not in TARGETS:assert current==old,'Unrelated sync/projection changed'
        elif section=='projection':
            for key,value in old.items():
                if key not in ['sale_status','product_version','content_hash']:assert current[key]==value
for goods in TARGETS:
    assert products[goods]['sale_status']==projection[goods]['sale_status']=='OFF_SALE'
    assert products[goods]['product_version']==projection[goods]['product_version']==sync[goods]['confirmed_version']==sync[goods]['target_version']==2 and sync[goods]['state']=='CONFIRMED'
normal=load(ROOT/'docs/cat04-main-products.json')['products'];normal_ids={x['goodsId'] for x in normal}
assert {x['goods_id'] for x in after['products'] if x['sale_status']=='ON_SALE'}==normal_ids and len(normal_ids)==6
assert len(before['products'])==len(after['products'])==67 and len(after['orders'])==71 and len(after['ledger'])==207
ux_before=load(WORK/'ux-before.json');ux_after=inv.snapshot('zj-market-ux');assert ux_before==ux_after,'UX facts changed';save(WORK/'ux-after.json',ux_after)
for item in normal:
    goods=item['goodsId'];st=next(x for x in after['inventory'] if x['goods_id']==goods);assert (st['available'],st['reserved'],st['sold'])==(20,0,0)
    p=products[goods];assert Decimal(str(p['original_price']))==Decimal(item['originalPrice']) and p['goods_name']==item['goodsName']
    binding=next(x for x in after['bindings'] if x['goods_id']==goods);activity=next(x for x in after['activities'] if x['activity_id']==binding['activity_id']);discount=next(x for x in after['discounts'] if x['discount_id']==activity['discount_id'])
    assert activity['target']==2 and activity['valid_time']==120 and activity['status']==1 and discount['market_plan']=='ZJ' and Decimal(discount['market_expr'])==10
    assert Decimal(str(p['original_price']))-Decimal(discount['market_expr'])==Decimal(item['payPrice'])
    active=inv.sql('zj-market-b06',f"SELECT JSON_OBJECT('active',COUNT(*)) FROM group_buy_market_b06.group_buy_activity WHERE activity_id={activity['activity_id']} AND status=1 AND start_time<=UTC_TIMESTAMP() AND end_time>UTC_TIMESTAMP();")
    assert active==[{'active':1}]
review=load(WORK/'ownership-review.json');assert review['status']=='REVIEWED' and set(review['goodsIds'])==TARGETS
assert review['reviews'][1]['originalFixtureRecovered'] is False and review['reviews'][1]['historicalOperatorIdUnavailable'] is True
for p,value in review['sourceHashes'].items():assert sha(Path(p))==value
seal=load(WORK/'evidence-before-retirement.json');assert seal['status']=='SAVED_BEFORE_RETIREMENT' and set(seal['goodsIds'])==TARGETS
for name,value in seal['files'].items():assert sha(WORK/name)==value,'Pre-retirement evidence changed'
assert load(WORK/'retirement.json')['status']=='PASS' and all(x['skipped'] for x in load(WORK/'retirement-repeat.json')['rows'])
assert load(WORK/'repeat-and-rollback-guard.json')['status']=='PASS'
browser=load(WORK/'browser-report.json');assert browser['status']=='PASS' and browser['strictTLS'] and not browser['ignoreHTTPSErrors'] and not browser['blockedBusinessMutations'] and len(browser['publicGoods'])==6 and len(browser['originalOrders'])==2
for mode in ['normal','empty','down','recovery']:assert load(WORK/('probe-ux-'+mode+'.json'))['status']=='PASS'
empty=load(WORK/'probe-ux-empty.json');assert empty['catalogueResponseControlledEmpty'] and not empty['actualCatalogueDataModified'] and empty['result']['catalogueTotal']==0 and empty['result']['signedTeamCode']=='TEAM_NOT_FOUND'
assert load(WORK/'probe-ux-down.json')['error']=='Signed team readiness failed'
contract=run(['node','scripts/cat02-probe.test.mjs']);assert '11 cases' in contract
freeze=load(WORK/'release-freeze.json');upgrade=load(WORK/'main-upgrade.json');assert upgrade['status']=='PASS' and upgrade['preExistingFactsPreserved']
assert sha(STABLE/'releases'/freeze['release']/'release.json')==freeze['releaseSha256'] and sha(STABLE/'releases'/freeze['previousRelease']/'release.json')==freeze['previousReleaseSha256']
backup=STABLE/'backups'/upgrade['backupBatch'];assert load(backup/'COMPLETE.json')['manifestSha256']==sha(backup/'manifest.json')
for name,item in load(backup/'manifest.json')['files'].items():
    p=(backup/name).resolve();assert p.is_relative_to(backup.resolve()) and sha(p)==item['sha256'],'Cold backup drift'
for file in (backup/'old-release').rglob('*'):
    if file.is_file():assert sha(file)==sha(STABLE/'releases'/freeze['previousRelease']/file.relative_to(backup/'old-release')),'Previous release changed'
private=STABLE/'private'/freeze['release'];manifest=load(private/'files-manifest.json');assert 'seed-goods-id.txt' not in manifest['probe']
assert not any('seed-goods-id' in item['relativePath'] for item in manifest['files'])
source=(STABLE/'releases'/freeze['release']/'controller.py').read_text(encoding='utf8');assert "('web-ca.pem', 'demo-accounts.json')" in source
probe_source=ROOT/'scripts/cat02-stable-probe.mjs';probe_runtime=STABLE/'releases'/freeze['release']/'stable-probe.mjs'
assert sha(probe_source)==freeze['probeSourceSha256'] and sha(probe_runtime)==freeze['tools']['stable-probe.mjs']
assert probe_source.read_text(encoding='utf8')==probe_runtime.read_text(encoding='utf8'),'Probe differs beyond Windows line endings'
stable=json.loads(run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',STABLE/'scripts/stable.ps1','-Action','ready']));assert stable['status']=='READY' and stable['release']==freeze['release']
live=json.loads(run(['node',STABLE/'releases'/freeze['release']/'stable-probe.mjs',private/manifest['probe']['web-ca.pem']['relativePath'],private/manifest['probe']['demo-accounts.json']['relativePath']]))
assert live['status']=='STABLE_PROBE_PASS' and live['catalogueTotal']==6 and live['signedTeamCode']=='TEAM_NOT_FOUND';save(WORK/'probe-main-after-retirement.json',live)
assert 'UX_GATE_OPEN' in run(['py','-B','scripts/b06-deployment.py','ready'])
isolation=json.loads(run(['py','-B','scripts/cat04-isolation.py']));assert isolation['status']=='PASS' and isolation['containerIds']['zj-market-ux']==load(WORK/'isolation-before-upgrade.json')['containerIds']['zj-market-ux'];save(WORK/'isolation-final.json',isolation)
old_release=load(backup/'old-release/release.json');new_release=load(STABLE/'releases'/freeze['release']/'release.json')
for field in ['images','volumes','networks','schemaFingerprint','flywayHistorySha256','discoveryIndexColumns']:assert old_release[field]==new_release[field],field
# Historical CAT reports remain frozen; this successor has separate evidence.
baseline_docs=load(ROOT/'.local/cat/cat01-5-20261020-01/documents-before.json')
for root in [ROOT,MAIN]:
    for name in ['docs/tests/cat01-1-acceptance.json','docs/tests/cat01-2-acceptance.json','docs/tests/cat01-3-acceptance.json','docs/tests/cat01-4-acceptance.json','docs/catalog-products.json','docs/cat04-main-products.json','docs/cat04-release.json']:assert sha(root/name)==baseline_docs[str(root)][name]
    assert sha(root/'docs/tests/cat01-5-acceptance.json')==load(ROOT/'.local/cat/cat01-5-20261020-01/resume-20261021/resume-proof.json')['frozenAcceptanceSha256']
report={'stage':'CAT-02 retained storefront closeout','status':'PASS','acceptedAt':datetime.now(timezone.utc).isoformat(),'batch':'cat02-closeout-20261021-01','summary':{'retiredLegacyGoods':2,'publicGoods':6,'allGoods':67,'orders':71,'ledgerRows':207,'newOrders':0,'newPaymentsOrRefunds':0,'newInventoryOperations':0,'originalBusinessFactsPreserved':True,'uxBusinessFactsPreserved':True},'scope':'Resolve both previously retained technical display goods; original CAT01.1-01.5 reports unchanged','retiredGoods':[{'goodsId':g,'goodsName':products[g]['goods_name'],'productVersion':2,'saleStatus':'OFF_SALE','aConfirmed':True} for g in sorted(TARGETS)],'ownershipReview':review,'checks':{'noSeedInActiveProbeOrManifest':True,'signedMissingTeamQueryRequiresSpecificSemantic404':True,'generic404AuthTLSDependencyAndMaintenanceFailuresRejected':True,'emptyCatalogueResponseBranchPassedWithRealUXPeer':True,'actualUXADownFailsAndRecovers':True,'allImagesAndSchemaUnchanged':True,'oldReleasesAndColdBackupVerified':True,'onlyTwoExactOptimisticOffSaleEdits':True,'preRetirementEvidenceHashesVerified':True,'repeatNoBusinessChanges':True,'legacyRollbackRefusedBeforeStoppingNewRelease':True,'exactSixNormalGoodsPublic':True,'fourBrowserViewportsAndSixImageHashes':True,'originalSeedOrdersSnapshotsReadable':True,'normalPriceStockAndActivityInvariantsAgainstAcceptedBaseline':True,'mainAndUXOriginalBusinessRecordsPreserved':True},'probeMain':live,'probeContractTests':contract.strip(),'browser':browser,'release':freeze,'upgrade':{k:upgrade[k] for k in ['release','backupBatch','backupManifestSha256','preExistingFactsPreserved']},'beforeDigests':inv.digests(before),'afterDigests':inv.digests(after),'uxBeforeDigests':inv.digests(ux_before),'uxAfterDigests':inv.digests(ux_after),'preservedHistoricalObligations':{'reconcilingTeams':sum(x['team_status']=='RECONCILING' for x in after['teams']),'unfinishedWork':sum(x['state'] not in ['DONE','DEAD'] for x in after['work']),'activeBlocks':sum(x['state']=='ACTIVE' for x in after['blocks']),'reviewOrders':sum(bool(x['review_required']) for x in after['orders']),'pendingFulfillment':sum(x['status']=='PENDING' for x in after['fulfillment'])},'boundaries':['Original fixture and individual creator identity for normal01 were not recovered; original outbox ID, complete fields, failed-batch documentation and zero-related-business records form the reviewed evidence chain under explicit current authorization.','Empty catalogue drill masks the read response on UX; no real catalogue rows were taken off sale for this drill. Signed peer/auth/TLS calls remained real.','Normal browser product inspection uses anonymous GET only. Prices/activity/stock are compared to accepted baselines and current activity windows; no new quote/purchase/payment requests on normal goods.','Original financial/review/reconciliation/fulfillment history is preserved; no claim of system-wide historical obligations cleared.','Legacy CAT04 rollback requires its original seed ON_SALE. With it retired the tool refuses before stopping the current release; fix forward or use a verified SKU-independent successor, never restore old data over live volumes.'],'privateEvidenceRoot':str(WORK),'sourceHashes':{p.name:sha(p) for p in sorted((ROOT/'scripts').glob('cat02-*')) if p.is_file()},'evidenceHashes':{p.name:sha(p) for p in WORK.glob('*.json') if p.is_file()},'screenshots':{p.name:sha(p) for p in WORK.glob('*.png')}}
for root in [ROOT,MAIN]:save(root/'docs/tests/cat02-closeout-acceptance.json',report);save(root/'docs/cat02-release.json',freeze)
print('CAT02_FINAL_ACCEPTANCE_PASS 2-retired/6-normal/no-new-trades/seed-independent-ready')
