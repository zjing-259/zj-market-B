"""Real executor interruption: child exits without finally; separate recover consumes the durable inverse."""
from pathlib import Path
import argparse,importlib.util,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('faults',ROOT/'scripts/b06-faults.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);p.add_argument('--child',action='store_true');a=p.parse_args()
 if a.child:
  obs=m.module('observer_lock',ROOT/'scripts/b06-observability.py')
  with m.deployment_lock(),obs.exclusive():
   f=m.Faults(a.run_name);f.d.capacity();f.d.ready();before=f.inspect('namesrv');f.report['initial']={k:before[k] for k in ('id','image','restart','command')};f.save()
   with f.down('namesrv'):
    m.atomic(f.work/'interrupted-observation.json',f.o.sample());f.event('intentional-executor-exit-without-finally',exitCode=73);os._exit(73)
  raise AssertionError('UNREACHABLE')
 r=subprocess.run([sys.executable,'-B',__file__,'--run-name',a.run_name,'--child'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
 work=m.HOME/a.run_name;(work/'interrupted-child.log').write_text(r.stdout+r.stderr,encoding='utf-8');m.require(r.returncode==73,'EXPECTED_CHILD_EXIT_73')
 journal=json.loads((work/'recovery.json').read_text());m.require(len(journal)==1 and journal[0]['service']=='namesrv','DURABLE_INVERSE_REQUIRED')
 r=subprocess.run([sys.executable,'-B',ROOT/'scripts/b06-faults.py','recover','--run-name',a.run_name],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240);(work/'separate-recover.log').write_text(r.stdout+r.stderr,encoding='utf-8');m.require(r.returncode==0,'SEPARATE_RECOVER_FAILED')
 obs=m.module('observer_lock_final',ROOT/'scripts/b06-observability.py')
 with m.deployment_lock(),obs.exclusive():
  f=m.Faults(a.run_name,True);v=f.inspect('namesrv');m.require(all(v[k]==f.report['initial'][k] for k in ('id','image','restart','command')) and not f.actions,'RECOVERY_DRIFT');f.check('separate-process-restored-original-container-and-policy',v['state']['Running'] and v['state']['Health']['Status']=='healthy');f.tools();f.transport();f.report.update(status='PASSED',finishedAt=m.stamp(),intentionalExitCode=73);f.save()
 print('INTERRUPTED_RECOVERY_PASS')
if __name__=='__main__':main()
