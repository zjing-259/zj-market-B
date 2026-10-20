"""Freeze evidence before cleanup; failed batches retain exact original identities too."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'.local/cat/cat01-3-20261020-01'
p=argparse.ArgumentParser();p.add_argument('--failed',action='store_true');a=p.parse_args()
f=json.loads((WORK/'fixture.json').read_text(encoding='utf-8'))
assert ROOT.name=='zj-market-ux' and f['project']=='zj-market-ux' and f['origin']=='https://zj-market-ux.test:8446'
lock=WORK/'evidence-lock.json'
if lock.exists():raise RuntimeError('Preserve already frozen evidence; cleanup may reuse original lock')
browser_file=WORK/'browser-report.json'
browser=json.loads(browser_file.read_text(encoding='utf-8')) if browser_file.exists() else None
if not a.failed:
    assert browser and browser['status']=='PASSED' and (WORK/'accounting-report.json').is_file()
else:
    assert browser is None or browser['status']!='PASSED','Do not relabel passed evidence as failed'
files={}
shutil.copy2(WORK/'fixture.json',WORK/'fixture-before-cleanup.json')
paths=[WORK/'fixture-before-cleanup.json']
if browser_file.exists():paths.append(browser_file)
if (WORK/'accounting-report.json').exists():
    shutil.copy2(WORK/'accounting-report.json',WORK/'accounting-before-cleanup.json');paths.append(WORK/'accounting-before-cleanup.json')
summary={'status':'FAILED_EVIDENCE_SAVED' if a.failed else 'PASSED_EVIDENCE_SAVED','batch':f['batch'],'savedAt':datetime.now(timezone.utc).isoformat(),'originalOrderIds':list(browser['orders']) if browser else [],'pendingIdentitiesPreserved':True,'cleanupDoesNotCancelOrRefundOrders':True}
(WORK/'evidence-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');paths.append(WORK/'evidence-summary.json')
for file in paths:files[file.name]=hashlib.sha256(file.read_bytes()).hexdigest().upper()
goods=[x['goodsId'] for x in f['items'] if x['purpose']=='ACCEPTANCE']
assert len(goods)==8 and len(set(goods))==8
value={'status':'SAVED_BEFORE_CLEANUP','batch':f['batch'],'project':'zj-market-ux','goodsIds':goods,'files':files,'failedBatch':a.failed}
lock.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print('CAT03_EVIDENCE_FROZEN exact-ids/original-operations/before-cleanup')
