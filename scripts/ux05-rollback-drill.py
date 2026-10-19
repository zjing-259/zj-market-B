"""Prove a compatible web rollback with CURRENT UX data, then restore accepted web."""
from pathlib import Path
import importlib.util,json,os,subprocess
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ux_deployment',ROOT/'scripts/b06-deployment.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
if ROOT.name!='zj-market-ux' or m.PROJECT!='zj-market-ux':raise RuntimeError('UX-only rollback drill')
d=m.Deployment('desktop-linux')
assert d.ready()['mode']=='open' and d.gateway_mode()=='open'
OLD='sha256:a3aad07bd5e4e5b06c4ec647cc72299f0bf3d1125fdda85157e9529054a950d9'
NEW='sha256:fdd4072544a5290a3d51f58b8d1cbd83cac02bcb6eb2a20abaf9f3b3a9bbc145'
work=ROOT/'.local/ux05'
def facts():
 return d.admin('ux05-rollback-current-facts',"SELECT order_id,business_status FROM zj_market_b06.b_market_order ORDER BY order_id; SELECT payment_id,gate,amount FROM zj_market_b06.b_sim_payment ORDER BY payment_id; SELECT refund_id,refunded_amount FROM zj_market_b06.b_sim_refund ORDER BY refund_id; SELECT goods_id,available,reserved,sold FROM zj_market_b06.b_inventory_account ORDER BY goods_id; SELECT ledger_id,kind FROM zj_market_b06.b_inventory_ledger ORDER BY ledger_id;")
before=facts()
override=work/'rollback-override.json'
override.write_text(json.dumps({'services':{'web':{'image':OLD,'volumes':[{'type':'bind','source':str(ROOT/'deploy/b06/nginx.conf'),'target':'/etc/nginx/nginx.conf','read_only':True,'bind':{'create_host_path':False}}]}}}))
try:
 d.gateway('maintenance')
 env=os.environ.copy();env['B06_ADMISSION_FILE']=str(ROOT/'deploy/b06/config/admission-maintenance.conf')
 result=subprocess.run(d.compose+['-f',str(m.CONTROL/'capabilities.yml'),'-f',str(override),'up','-d','--no-deps','--force-recreate','--wait','--wait-timeout','90','web'],env=env,capture_output=True,text=True,timeout=150)
 if result.returncode:raise RuntimeError('Compatible UX rollback failed')
 assert subprocess.check_output(d.docker+['inspect','--format','{{.Image}}','zj-market-ux-web-1'],text=True).strip()==OLD
 assert d.gateway_mode()=='maintenance'
 assert before==facts()
finally:d.gateway('open')
assert subprocess.check_output(d.docker+['inspect','--format','{{.Image}}','zj-market-ux-web-1'],text=True).strip()==NEW
assert d.ready()['mode']=='open' and d.gateway_mode()=='open' and before==facts()
(work/'rollback-drill.json').write_text(json.dumps({'status':'PASS','project':'zj-market-ux','oldWebImage':OLD,'restoredWebImage':NEW,'currentOrdersFundsRefundsStockLedgerPreserved':True,'restoredFromBackup':False,'gateway':'open'},indent=2)+'\n')
print('UX05_ROLLBACK_DRILL_PASS current-data-preserved/accepted-web-restored')
