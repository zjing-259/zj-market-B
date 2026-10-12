"""Child exits after durable original-stack stop; a separate CLI process recovers from disk."""
from pathlib import Path
import argparse,importlib.util,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('recovery',ROOT/'scripts/b06-backup.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);p.add_argument('--child',action='store_true');a=p.parse_args();m.valid_name(a.run_name)
 if a.child:
  lock=m.module('fault_lock',ROOT/'scripts/b06-faults.py');obs=m.module('obs_lock',ROOT/'scripts/b06-observability.py')
  with lock.deployment_lock(),obs.exclusive():
   r=m.Recovery(a.run_name);r.preflight();r.interrupt_original();r.event('intentional-executor-exit-without-finally',exitCode=73);os._exit(73)
 result=subprocess.run([sys.executable,'-B',__file__,'--run-name',a.run_name,'--child'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);work=m.HOME/a.run_name;(work/'interrupted-child.log').write_text(result.stdout+result.stderr,encoding='utf-8');m.require(result.returncode==73,'EXPECTED_CHILD_EXIT_73');m.require(json.loads((work/'recovery.json').read_text()).get('restoreOriginal'),'DURABLE_ORIGINAL_RECOVERY_INTENT_REQUIRED')
 result=subprocess.run([sys.executable,'-B',ROOT/'scripts/b06-backup.py','recover','--run-name',a.run_name],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=420);(work/'independent-recover.log').write_text(result.stdout+result.stderr,encoding='utf-8');m.require(result.returncode==0,'INDEPENDENT_ORIGINAL_RECOVERY_FAILED');m.require(json.loads((work/'recovery.json').read_text())=={},'RECOVERY_INTENT_REMAINS')
 p=work/'progress.json';r=json.loads(p.read_text(encoding='utf-8'));m.require(any(c['name']=='original-funds-stock-quotas-inbox-preserved' for c in r['checks']),'MISSING_FINAL_FINANCIAL_PROOF');r.update(status='PASSED',finishedAt=m.stamp(),intentionalExitCode=73,independentRecoverProcess=True);m.atomic(p,r);print('B066_INDEPENDENT_INTERRUPTED_RECOVERY_PASS')
if __name__=='__main__':main()
