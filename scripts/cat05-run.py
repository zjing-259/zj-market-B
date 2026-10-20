"""Owned main acceptance lifecycle. Default plan is read-only; never restores live data."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, os, re, subprocess
ROOT=Path(__file__).resolve().parents[1]
STABLE=Path('D:/Java/zj-market-stable')
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def save(p,v):
    temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(temp,p)
def inventory():
    s=importlib.util.spec_from_file_location('cat_inventory',ROOT/'scripts/cat01-inventory.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def seal(work,batch,failed=False):
    lock=work/'evidence-lock.json'
    if lock.exists():
        e=load(lock)
        assert e['batch']==batch and e['project']=='zj-market-b06'
        assert all(sha(work/name)==value for name,value in e['files'].items()),'Saved evidence changed'
        print('CAT05_EVIDENCE_ALREADY_SEALED');return
    f=load(work/'fixture.json');assert f['batch']==batch and f['project']=='zj-market-b06'
    names=['fixture.json','main-before.json','ux-before.json','browser-report.json','accounting-report.json','guards.json','stockout.json','original-receipt-recovery.json']
    frozen={}
    for name in names:
        p=work/name
        if p.exists():
            dest=work/('saved-'+name);dest.write_bytes(p.read_bytes());frozen[dest.name]=sha(dest)
    if not failed:assert load(work/'browser-report.json')['status']=='PASSED' and load(work/'accounting-report.json')['status']=='PASSED_REAL_BROWSER_ACCOUNTING'
    assert len(frozen)>=2
    ids=[x['goodsId'] for x in f['items'] if x['purpose']=='ACCEPTANCE' and x.get('goodsId')]
    assert ids and len(set(ids))==len(ids)
    unresolved=[x['key'] for x in f['items'] if x.get('createStarted') and not x.get('goodsId')]
    save(lock,{'status':'SAVED_BEFORE_CLEANUP','batch':batch,'project':'zj-market-b06','atUtc':datetime.now(timezone.utc).isoformat(),'failedBatch':failed,'goodsIds':ids,'files':frozen,'unknownCreateOutcomes':unresolved,'recovery':'retain original keys and browser state; inspect original operations, never create replacements'})
    print('CAT05_EVIDENCE_SEALED before-cleanup')
def main():
    p=argparse.ArgumentParser();p.add_argument('action',nargs='?',default='plan',choices=['plan','capture','prepare','configure','publish','verify','guards','stockout','browser','collect','seal','cleanup','final-browser','finalize','all']);p.add_argument('--batch',required=True);p.add_argument('--failed',action='store_true');a=p.parse_args()
    if ROOT.name!='zj-market-ux' or not re.fullmatch(r'cat01-5-[0-9]{8}-[0-9]{2}',a.batch):raise RuntimeError('Explicit owned CAT05 root/batch required')
    work=ROOT/'.local/cat'/a.batch
    if a.action=='plan':
        f=load(work/'fixture.json') if (work/'fixture.json').exists() else None
        print(json.dumps({'batch':a.batch,'origin':'https://zj-market.test','write':False,'phase':f.get('phase') if f else 'NOT_STARTED','ownedSamples':[x.get('goodsId') for x in f['items']] if f else [],'showcaseIsReadOnly':True,'flow':'all: capture -> original receipt drills -> configure/publish -> guards -> browser/accounting -> repeat/evidence -> seal -> owned cleanup/recovery -> final browser/accounting -> finalize'},indent=2));return
    env=dict(os.environ,CAT_ACCEPTANCE_BATCH=a.batch)
    def run(cmd):subprocess.run(cmd,cwd=ROOT,env=env,check=True)
    if a.action=='capture':
        if (work/'main-before.json').exists():raise RuntimeError('Original baseline exists; never overwrite')
        m=inventory();work.mkdir(parents=True,exist_ok=True)
        stable=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(STABLE/'scripts/stable.ps1'),'-Action','ready'],text=True));assert stable['status']=='READY'
        isolation=json.loads(subprocess.check_output(['py','-B','scripts/cat04-isolation.py'],cwd=ROOT,text=True));save(work/'isolation-before.json',isolation)
        for project,name in [('zj-market-b06','main'),('zj-market-ux','ux')]:save(work/(name+'-before.json'),m.snapshot(project))
        save(work/'documents-before.json',{str(root):{str(file.relative_to(root)).replace('\\','/'):sha(file) for file in (root/'docs').rglob('*') if file.is_file()} for root in [ROOT,Path('D:/Java/zj-market'),Path('D:/Java/group-buy-market')]})
        print('CAT05_BASELINE_CAPTURED');return
    if a.action=='seal':seal(work,a.batch,a.failed);return
    if a.action=='all':
        if (work/'evidence-lock.json').exists() or (work/'fixture.json').exists() and load(work/'fixture.json').get('phase')=='CLEANED':raise RuntimeError('Sealed batch: plan/owned cleanup only; do not rerun trades')
        if not (work/'main-before.json').exists():run(['py','-B',__file__,'capture','--batch',a.batch])
        try:
            run(['py','-B','scripts/cat05-checks.py','prepare'])
            for action in ['configure','publish','verify','guards','stockout','browser','collect']:run(['py','-B',__file__,action,'--batch',a.batch])
            for check in ['repeat','evidence']:run(['py','-B','scripts/cat05-checks.py',check])
        except Exception:
            # Cleanup may fail during dependency outage: retain both the error and all original keys.
            save(work/'failed-run.json',{'status':'FAILED_REQUIRES_ORIGINAL_RECORD_RECOVERY','batch':a.batch,'atUtc':datetime.now(timezone.utc).isoformat()})
            if (work/'fixture.json').exists():
                try:seal(work,a.batch,True);run(['node','scripts/cat05-products.mjs','cleanup'])
                except Exception:save(work/'cleanup-pending.json',{'status':'PENDING','batch':a.batch,'action':'recover original dependency/operation then repeat owned cleanup; no replacements'})
            raise
        try:
            run(['py','-B',__file__,'seal','--batch',a.batch])
            for check in ['cleanup','sealed']:run(['py','-B','scripts/cat05-checks.py',check])
            for action in ['final-browser','collect','finalize']:run(['py','-B',__file__,action,'--batch',a.batch])
        except Exception:
            save(work/'cleanup-pending.json',{'status':'PENDING_VERIFICATION_OR_CLEANUP','batch':a.batch,'action':'inspect saved evidence and original operations; repeat owned cleanup/read-only checks, never recreate trades'})
            raise
        return
    if not (work/'main-before.json').is_file():raise RuntimeError('Capture and review baseline first')
    if a.action in ['browser','final-browser']:
        adoption=load(STABLE/'state/adoption.json');private=STABLE/'private'/adoption['release'];manifest=load(private/'files-manifest.json');ca=(private/manifest['probe']['web-ca.pem']['relativePath']).resolve();assert ca.is_relative_to(private.resolve());env['NODE_EXTRA_CA_CERTS']=str(ca)
    if a.action in ['prepare','publish','verify','guards','stockout','cleanup']:run(['node','scripts/cat05-products.mjs',a.action])
    elif a.action=='configure':run(['py','-B','scripts/cat05-configure.py'])
    elif a.action=='browser':run(['node','scripts/cat05-browser.mjs'])
    elif a.action=='collect':run(['py','-B','scripts/cat05-accounting.py','--batch',a.batch])
    elif a.action=='final-browser':run(['node','scripts/cat05-final-browser.mjs'])
    elif a.action=='finalize':run(['py','-B','scripts/cat05-finalize.py'])
if __name__=='__main__':main()
