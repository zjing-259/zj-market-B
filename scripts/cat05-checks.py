"""Acceptance protocol drills; preserve original keys and run only an explicit main batch."""
from pathlib import Path
import argparse,importlib.util,json,os,re,subprocess
ROOT=Path(__file__).resolve().parents[1];BATCH=os.environ.get('CAT_ACCEPTANCE_BATCH','cat01-5-20261020-01');WORK=ROOT/'.local/cat'/BATCH
assert ROOT.name=='zj-market-ux' and re.fullmatch(r'cat01-5-[0-9]{8}-[0-9]{2}',BATCH)
def load(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def call(cmd,env=None):subprocess.run(cmd,cwd=ROOT,env=env,check=True)
def inject(flags,expected,name,env=None):
    p=subprocess.run(['node','scripts/cat05-products.mjs',*flags],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf8')
    (WORK/name).write_text(p.stdout+p.stderr,encoding='utf8')
    assert p.returncode!=0 and expected in p.stderr,'Unexpected response; retain original records and inspect private log'
    return {'flags':flags,'expectedInjection':expected,'exitCode':p.returncode}
def prepare():
    proof=WORK/'original-receipt-recovery.json'
    if proof.exists():assert load(proof)['status']=='PASS';print('CAT05_PREPARE_DRILLS_ALREADY_SAVED');return
    assert not (WORK/'fixture.json').exists(),'Original preparation started without drill evidence; inspect it rather than injecting again'
    rows=[inject(['prepare','--lose-create-response'],'INJECTED_CREATE_RESPONSE_LOSS','prepare-create-loss.txt'),inject(['prepare','--lose-stock-response'],'INJECTED_STOCK_RESPONSE_LOSS','prepare-inbound-loss.txt')]
    call(['node','scripts/cat05-products.mjs','prepare'])
    item=next(x for x in load(WORK/'fixture.json')['items'] if x['key']=='success');assert item['recoveredCreate'] and item['stockOutcomeUnknown'] and item['stockConfirmed']
    save(proof,{'status':'PASS','scope':'controlled receipt loss after actual acceptance; original product/inbound operation recovered','runs':rows})
def repeat():
    inv=module('inv','cat01-inventory.py');b=inv.snapshot('zj-market-b06');save(WORK/'repeat-before.json',b)
    call(['node','scripts/cat05-products.mjs','prepare']);call(['py','-B','scripts/cat05-configure.py'])
    a=inv.snapshot('zj-market-b06');save(WORK/'repeat-after.json',a);assert a==b,'Business facts changed during repeat; inspect without resetting data'
    save(WORK/'repeat-proof.json',{'status':'PASS','mainBusinessDigestsBefore':inv.digests(b),'mainBusinessDigestsAfter':inv.digests(a),'sameOriginalGoodsAndStockKeys':True,'businessChanges':0})
def evidence():
    runner=module('runner','cat05-run.py');f=load(WORK/'fixture.json');drill=WORK/'failed-evidence-drill';drill.mkdir(exist_ok=True)
    if not (drill/'evidence-lock.json').exists():
        save(drill/'fixture.json',f);save(drill/'browser-report.json',{'status':'FAILED','originalRequestsRetained':True})
    runner.seal(drill,BATCH,True);runner.seal(drill,BATCH,True)
    lock=load(drill/'evidence-lock.json');saved=load(drill/'saved-fixture.json')
    assert lock['failedBatch'] and set(lock['goodsIds'])=={x['goodsId'] for x in f['items']}
    assert [(x['goodsId'],x.get('stockRequest')) for x in saved['items']]==[(x['goodsId'],x.get('stockRequest')) for x in f['items']]
    save(WORK/'failure-evidence-guard.json',{'status':'PASS','scope':'offline evidence-only failed-batch guard; no business API or replacement operations','failedMarkerRetained':True,'originalOperationRequestsRetained':True,'repeatSealChecksOriginalHashes':True})
    inv=module('inv','cat01-inventory.py');before=inv.snapshot('zj-market-b06');rows=[]
    for cmd in [['py','-B','scripts/ux05-joint.py','prepare','--target','main','--batch','ux05-20261020-99'],['node','scripts/ux05-browser.mjs','prepare','main','ux05-20261020-99']]:
        p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf8');assert p.returncode and 'retired' in p.stderr
        rows.append({'entry':cmd[2] if cmd[0]=='py' else cmd[1],'exitCode':p.returncode,'rejectedBeforeBusinessWrites':True})
    assert before==inv.snapshot('zj-market-b06')
    save(WORK/'legacy-entry-guards.json',{'status':'PASS','results':rows,'mainBusinessFactsUnchanged':True})
def cleanup():
    proof=WORK/'cleanup-receipt-recovery.json'
    if proof.exists():assert load(proof)['status']=='PASS'
    else:
        env=dict(os.environ,CAT_LOSE_OFFSALE_RECEIPT='badimage')
        inject(['cleanup'],'INJECTED_OFFSALE_RESPONSE_LOSS','cleanup-receipt-loss.txt',env)
        call(['node','scripts/cat05-products.mjs','cleanup'])
        item=next(x for x in load(WORK/'fixture.json')['items'] if x['key']=='badimage');assert item['recoveredEdit'] and not item['editStarted']
        save(proof,{'status':'PASS','controlledLossAfterActualAcceptance':True,'goodsId':item['goodsId'],'originalEditRecovered':True,'finalVersion':item['version'],'noReplacementProductOrRepeatEdit':True})
    call(['node','scripts/cat05-products.mjs','cleanup'])
def sealed():
    script="""import path from 'node:path';import{fixture,work,Client,setSale,validateCleanupIds,save}from './scripts/cat05-lib.mjs';const f=fixture(),c=new Client();let rejected=0;for(const fn of[()=>setSale(c,'success','ON_SALE'),()=>c.request('/admin/products','POST',f.items[0].fields),()=>c.request('/admin/inventory/'+f.items[0].goodsId+'/inbounds','POST',f.items[0].stockRequest),()=>Promise.resolve(validateCleanupIds([f.showcase[0].goodsId])),()=>Promise.resolve(validateCleanupIds(['5a4d973a-4d83-4f7b-9155-4c331b436fc4']))]){try{await fn()}catch{rejected++}}if(rejected!==5||c.trace.length!==0)throw Error('Unsafe sealed operation allowed');save(path.join(work,'sealed-guards.json'),{status:'PASS',rejectedActions:5,networkRequests:0,normalAndProbeNotOwned:true,sealedNoPublishCreateInbound:true});"""
    subprocess.run(['node','--input-type=module','-'],input=script,cwd=ROOT,text=True,check=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','repeat','evidence','cleanup','sealed']);a=p.parse_args()
    assert (WORK/'main-before.json').exists(),'Capture original main baseline first'
    globals()[a.action]();print('CAT05_PROTOCOL_CHECK_PASS '+a.action)
