"""Fresh real-stack B063 acceptance; no resets, old reports preserved."""
from pathlib import Path
import argparse,importlib.util,json,subprocess,hashlib,re,datetime
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);args=p.parse_args()
 if not re.fullmatch(r'b063-[a-z0-9-]+',args.run_name):raise RuntimeError('Use fresh b063 batch')
 work=ROOT/'.local/b06/browser'/args.run_name
 if work.exists():raise RuntimeError('Batch already exists; refusing overwrite')
 work.parent.mkdir(parents=True,exist_ok=True)
 # Probe real Edge without certificate bypass BEFORE business writes.
 probe="""import {createRequire} from 'node:module';import path from 'node:path';const require=createRequire(path.resolve('target/b06-browser-runtime/package.json'));const {chromium}=require('playwright');const b=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',args:['--host-resolver-rules=MAP zj-market.test 127.0.0.1','--no-proxy-server']});try{const p=await b.newPage({ignoreHTTPSErrors:false});await p.goto('https://zj-market.test');if(!await p.evaluate(()=>isSecureContext&&!!navigator.locks))throw Error('Secure context missing')}finally{await b.close()}"""
 subprocess.run(['node','--input-type=module','-e',probe],cwd=ROOT,check=True)
 spec=importlib.util.spec_from_file_location('deployment',ROOT/'scripts/b06-deployment.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);d=m.Deployment('desktop-linux');d.ready()
 if d.state().get('mode')!='open' or d.state().get('phase')!='READY':raise RuntimeError('Explicit open/READY deployment required')
 hosts=Path('C:/Windows/System32/drivers/etc/hosts');before=hashlib.sha256(hosts.read_bytes()).hexdigest()
 shared=lambda:subprocess.check_output(d.docker+['ps','-a','--filter','label=com.docker.compose.project!=zj-market-b06','--format','{{.ID}} {{.Names}} {{.Image}} {{.State}}'],text=True)
 snapshot=shared()
 subprocess.run(['node','docs/tests/b06-normal-browser.mjs','prepare',args.run_name],cwd=ROOT,check=True)
 fpath=work/'fixture.json';f=json.loads(fpath.read_text());f['activities']={}
 # New numeric IDs compatible with the frozen A Mapper; no updates to existing activity/team.
 base=int(d.admin('next-b063-activity',"SELECT GREATEST(630000,COALESCE(MAX(activity_id),0))+1 FROM group_buy_market_b06.group_buy_activity;").strip())
 for i,(name,goods) in enumerate(f['goods'].items()):
  activity=base+i;discount=activity*100+1;minutes=2 if name=='expiry' else 15
  sql=f"USE group_buy_market_b06; START TRANSACTION; INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) VALUES ('{discount}','B063 {name}','Ten yuan reduction',0,'ZJ','10'); INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time) VALUES ({activity},'B063 {name}','{discount}',1,10,2,{minutes},1,UTC_TIMESTAMP()-INTERVAL 1 HOUR,UTC_TIMESTAMP()+INTERVAL 30 DAY); INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES ('b06','web',{activity},'{goods}'); COMMIT;"
  d.admin('b063-config-'+name,sql);f['activities'][name]={'activityId':activity,'discountId':discount,'validMinutes':minutes};fpath.write_text(json.dumps(f,indent=2))
 with (work/'browser.log').open('w',encoding='utf-8') as log:result=subprocess.run(['node','docs/tests/b06-normal-browser.mjs','browser',args.run_name],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 if result.returncode:raise RuntimeError('Browser acceptance failed; retained private batch, do not reuse')
 if hashlib.sha256(hosts.read_bytes()).hexdigest()!=before:raise RuntimeError('hosts changed during acceptance')
 if snapshot!=shared():raise RuntimeError('Shared container state changed')
 subprocess.run(['python','-B','docs/tests/collect-b06-normal.py','--run-name',args.run_name],cwd=ROOT,check=True)
 print('PASS B063 actual browser and conservation')
if __name__=='__main__':main()
