"""UX-only fault drills with owned service restoration in finally blocks."""
from pathlib import Path
import importlib.util, json, subprocess, time
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ux_deployment',ROOT/'scripts/b06-deployment.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
if ROOT.name!='zj-market-ux' or m.PROJECT!='zj-market-ux':raise RuntimeError('UX-only drills')
d=m.Deployment('desktop-linux')
if d.ready().get('mode')!='open' or d.gateway_mode()!='open':raise RuntimeError('Open healthy UX required')
names=['zj-market-b06-'+x+'-1' for x in ['mysql','redis','namesrv','broker','marketing-a','market-b','web']]
def identities():return subprocess.check_output(d.docker+['inspect','--format','{{.Id}} {{.Image}}',*names],text=True).splitlines()
before=identities();checks=[]
def probe(mode):
 r=subprocess.run(['node','scripts/ux05-fault-probe.mjs',mode],cwd=ROOT,capture_output=True,text=True,timeout=100)
 if r.returncode:raise RuntimeError('Fault probe failed '+mode)
 result=json.loads(r.stdout);checks.append(result);print('PASS '+mode,flush=True)
def restore(service):
 subprocess.run(d.docker+['start','zj-market-ux-'+service+'-1'],check=True,capture_output=True)
 deadline=time.time()+150
 while time.time()<deadline:
  status=subprocess.check_output(d.docker+['inspect','--format','{{.State.Health.Status}}','zj-market-ux-'+service+'-1'],text=True).strip()
  if status=='healthy':return
  time.sleep(2)
 raise RuntimeError('Owned service did not recover '+service)
try:
 d.gateway('maintenance');probe('maintenance')
finally:d.gateway('open')
probe('open')
owned_before=subprocess.check_output(d.docker+['inspect','--format','{{.Id}}','zj-market-ux-web-1','zj-market-ux-market-b-1'],text=True)
try:d.preflight_start(d.state(),'maintenance','start')
except RuntimeError as e:
 if 'already running' not in str(e):raise
else:raise RuntimeError('Duplicate start not rejected')
assert owned_before==subprocess.check_output(d.docker+['inspect','--format','{{.Id}}','zj-market-ux-web-1','zj-market-ux-market-b-1'],text=True)
checks.append({'mode':'duplicate-start','status':'PASS','containersUnchanged':True})
for service,mode in [('market-b','b-down'),('marketing-a','a-down')]:
 try:
  subprocess.run(d.docker+['stop','zj-market-ux-'+service+'-1'],check=True,capture_output=True)
  probe(mode)
 finally:restore(service)
probe('open');assert d.ready()['mode']=='open' and d.gateway_mode()=='open'
assert before==identities()
(ROOT/'.local/ux05/faults.json').write_text(json.dumps({'status':'PASS','checks':checks,'mainContainerIdentitiesUnchanged':True},indent=2)+'\n')
print('UX05_FAULTS_PASS restored-open/main-unchanged')
