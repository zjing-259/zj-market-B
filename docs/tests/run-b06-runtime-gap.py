"""Verify documented recovery when B disappears between remove/create in an interrupted recreation.
Only the owned ephemeral B container is removed; no -v, no volume/schema/business mutation.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('faults',ROOT/'scripts/b06-faults.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
SQL="SELECT order_id,payment_id,amount,funds_state,a_acceptance,success_hash,paid_at_ms FROM zj_market_b06.b_payment ORDER BY order_id; SELECT order_id,refund_id,amount,funds_status,sync_status,release_status,success_hash FROM zj_market_b06.b_refund ORDER BY order_id,refund_id; SELECT order_id,kind,goods_id,delta_available FROM zj_market_b06.b_inventory_ledger ORDER BY order_id,kind; SELECT team_id,reserved_count,paid_count FROM group_buy_market_b06.ab_team ORDER BY team_id;"
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);p.add_argument('--child',action='store_true');a=p.parse_args();obs=m.module('observer_lock',ROOT/'scripts/b06-observability.py')
 if a.child:
  with m.deployment_lock(),obs.exclusive():
   f=m.Faults(a.run_name);f.d.capacity();f.d.ready();before=f.inspect('market-b');f.report['initial']={k:before[k] for k in ('id','image','restart','command','extraHosts')};f.report['financialHashBefore']=hashlib.sha256(f.query(SQL).encode()).hexdigest();f.save()
   f.remember({'kind':'runtime','service':'market-b','baseline':before,'savedAt':m.stamp()});f.docker('stop-owned-b',['stop','--time','10',before['id']]);f.docker('remove-only-ephemeral-b',['rm',before['id']]);m.atomic(f.work/'missing-B-observation.json',f.o.sample());f.event('intentional-exit-in-runtime-recreation-gap',exitCode=73);os._exit(73)
 def invoke(label,args,timeout=240):
  r=subprocess.run([str(x) for x in args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout);(m.HOME/a.run_name/(label+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8');return r
 r=invoke('interrupted-child',[sys.executable,'-B',__file__,'--run-name',a.run_name,'--child'],120);m.require(r.returncode==73,'EXPECTED_CHILD_EXIT_73')
 work=m.HOME/a.run_name;journal=json.loads((work/'recovery.json').read_text());m.require(len(journal)==1 and journal[0]['kind']=='runtime','RUNTIME_INVERSE_REQUIRED')
 r=invoke('missing-container-recover-refused',[sys.executable,'-B',ROOT/'scripts/b06-faults.py','recover','--run-name',a.run_name]);m.require(r.returncode!=0 and 'RECOVERY_INCOMPLETE' in r.stderr,'MISSING_CONTAINER_MUST_NOT_BE_ADOPTED');m.require(len(json.loads((work/'recovery.json').read_text()))==1,'FAILED_INVERSE_MUST_REMAIN')
 # Explicit documented fallback, using the already authorized original owned deployment controller.
 r=invoke('controlled-open-fallback',[sys.executable,'-B',ROOT/'scripts/b06-deployment.py','open','--context','desktop-linux'],360);m.require(r.returncode==0,'CONTROLLED_OPEN_FAILED')
 r=invoke('recover-after-controlled-open',[sys.executable,'-B',ROOT/'scripts/b06-faults.py','recover','--run-name',a.run_name]);m.require(r.returncode==0,'FINAL_RECOVER_FAILED')
 with m.deployment_lock(),obs.exclusive():
  f=m.Faults(a.run_name,True);v=f.inspect('market-b');f.check('runtime-gap-recovered-original-image-command-hosts-policy',all(v[k]==f.report['initial'][k] for k in ('image','restart','command','extraHosts')) and v['id']!=f.report['initial']['id'] and not f.actions)
  f.check('funds-stock-and-team-quotas-unchanged-after-runtime-gap',hashlib.sha256(f.query(SQL).encode()).hexdigest()==f.report['financialHashBefore']);f.check('controlled-open-state-restored',f.d.state()['mode']=='open' and f.d.state()['phase']=='READY');f.run('final-actual-readiness',['node',ROOT/'docs/tests/b06-startup-client.mjs','ready',ROOT/'.local/b06/control',ROOT/'.local/b06/runtime'],timeout=150);f.report.update(status='PASSED',finishedAt=m.stamp(),intentionalExitCode=73,explicitControlledOpenFallback=True);f.save()
 print('RUNTIME_GAP_RECOVERY_PASS')
if __name__=='__main__':main()
