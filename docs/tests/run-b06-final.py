"""Final pinned-candidate browser acceptance in a fresh restored project.
Uses B066's durable journal, ownership, locks and independent recovery CLI.
"""
from pathlib import Path
import argparse, json, os, subprocess, hashlib, importlib.util
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
backup=load('final_backup',ROOT/'scripts/b06-backup.py')
class FinalRecovery(backup.Recovery):
 def release_test(self):
  super().release_test()
  work=self.work/'final-browser';name='b063-final-'+self.name.removeprefix('b066-')
  env=dict(os.environ,B06_BROWSER_WORK=str(work),B06_BROWSER_CONTROL=str(self.work/'restore-files/control'),B06_BROWSER_RUNTIME=str(self.work/'restore-files/runtime'),B06_BROWSER_STAGE='B-06.7')
  def browser(mode):
   with (self.work/('final-browser-'+mode+'.log')).open('w',encoding='utf-8') as log:
    r=subprocess.run(['node','docs/tests/b06-normal-browser.mjs',mode,name],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=480)
   backup.require(r.returncode==0,'FINAL_BROWSER_'+mode.upper()+'_FAILED')
  browser('prepare')
  f=json.loads((work/'fixture.json').read_text());f['activities']={}
  base=int(self.sql(self.clone,"SELECT GREATEST(670000,COALESCE(MAX(activity_id),0))+1 FROM group_buy_market_b06.group_buy_activity;").strip())
  for i,(kind,goods) in enumerate(f['goods'].items()):
   backup.require(bool(__import__('re').fullmatch('[a-f0-9-]{36}',goods)),'INVALID_BROWSER_GOODS')
   activity=base+i;discount=activity*100+1;minutes=2 if kind=='expiry' else 15
   self.sql(self.clone,f"USE group_buy_market_b06; START TRANSACTION; INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) VALUES ('{discount}','B067 {kind}','Ten yuan reduction',0,'ZJ','10'); INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time) VALUES ({activity},'B067 {kind}','{discount}',1,10,2,{minutes},1,UTC_TIMESTAMP()-INTERVAL 1 HOUR,UTC_TIMESTAMP()+INTERVAL 30 DAY); INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES ('b06','web',{activity},'{goods}'); COMMIT;")
   f['activities'][kind]={'activityId':activity,'discountId':discount,'validMinutes':minutes}
  backup.atomic(work/'fixture.json',f);browser('browser')
  self.run('final-browser-actual-accounting',['python','-B',ROOT/'docs/tests/collect-b06-normal.py','--run-name',name,'--work-dir',work,'--project',self.clone,'--control',self.work/'restore-files/control','--runtime',self.work/'restore-files/runtime','--compose',self.clone_config(),'--deployment-root',self.work/'restore-files/repo','--output',self.work/'final-browser-acceptance.json','--stage','B-06.7'],timeout=180)
  evidence=json.loads((self.work/'final-browser-acceptance.json').read_text())
  pins=json.loads((ROOT/'docs/b06-backup-release.json').read_text())['ordinaryImages']
  self.check('final-candidate-real-browser-and-accounting',evidence['stageCompletion'] and all(evidence['images'][service]==pins[key] for service,key in [('marketing-a','a'),('market-b','b'),('web','web')]))
  self.report['finalBrowser']={'browserChecks':len(evidence['browserChecks']),'accountingChecks':len(evidence['accountingChecks']),'reportSha256':backup.sha(self.work/'final-browser-acceptance.json')};self.save()
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);p.add_argument('--from-backup',required=True);a=p.parse_args()
 faults=load('final_faults',ROOT/'scripts/b06-faults.py');obs=load('final_observer',ROOT/'scripts/b06-observability.py')
 with faults.deployment_lock(),obs.exclusive():
  r=FinalRecovery(a.run_name);r.report['finalAcceptanceSourceSha256']={f:backup.sha(ROOT/f) for f in ['docs/tests/run-b06-final.py','docs/tests/b06-normal-browser.mjs','docs/tests/collect-b06-normal.py']};r.save();r.execute_restore(a.from_backup)
  o=obs.Observer().sample();backup.require(o['complete'] and not any(v['active'] for v in obs.load('alerts-state.json',{}).values()),'FINAL_ORIGINAL_OBSERVATION_NOT_HEALTHY')
  evidence=json.loads((r.work/'final-browser-acceptance.json').read_text())
  evidence.update(status='PASSED_WINDOWS_FINAL_PINNED_CANDIDATE',generatedAt=datetime.now(timezone.utc).isoformat(),restoredProject=r.clone,sourceBackupRun=a.from_backup,sourceBackupManifestSha256=backup.sha(backup.HOME/a.from_backup/'manifest.json'),recoveryRun=a.run_name,rawRecoveryReportSha256=backup.sha(r.work/'progress.json'),recoveryChecks=r.report['checks'],finalAcceptanceSourceSha256=r.report['finalAcceptanceSourceSha256'],originalRestored=True,originalFinancialSha256=r.report['originalFinancialBefore'],originalChannelSha256=r.report['originalChannelsBefore'],originalExternalUnchanged=True,originalObservationComplete=True,activeAlerts=0,newEnvironmentScope='Fresh empty named volumes restored from sealed backup; B062 blank business database initialization is separate historical evidence',allRecoveryJournalsEmpty=not r.journal)
  text=json.dumps(evidence,ensure_ascii=False,indent=2)+'\n'
  for v in r.d.values.values():backup.require(str(v) not in text,'PUBLIC_SECRET')
  for v in json.loads((ROOT/'.local/b06/control/demo-accounts.json').read_text()).values():backup.require(v['password'] not in text,'PUBLIC_ACCOUNT_SECRET')
  (ROOT/'docs/tests/b06-final-acceptance.json').write_text(text,encoding='utf-8');print('B067_FINAL_PINNED_CANDIDATE_PASS',flush=True)
if __name__=='__main__':main()
