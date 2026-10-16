"""Run current B against the sealed old A image, then restore current A in clone only."""
from pathlib import Path
import argparse,copy,datetime,json,re,subprocess,time
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);a=p.parse_args()
 if not re.fullmatch(r'td04_[0-9]{8}_[0-9]{2}',a.run_name):raise ValueError('Invalid run')
 work=ROOT/'target/team-discovery'/a.run_name;original=work/'compose.json';config=json.loads(original.read_text());project=config['name']
 if project!='zj-market-'+a.run_name.replace('_','-'):raise RuntimeError('Wrong project')
 old=copy.deepcopy(config);mounts=old['services']['marketing-a']['volumes'];old['services']['marketing-a']['volumes']=[m for m in mounts if m['target']!='/app/app.jar']
 if len(old['services']['marketing-a']['volumes'])!=len(mounts)-1:raise RuntimeError('Current A mount not found')
 old_path=work/'compose-old-a.json';old_path.write_text(json.dumps(old,indent=2)+'\n')
 docker=['docker','--context','desktop-linux'];evidence={'stage':'TD-04','status':'RUNNING','project':project,'checks':[]}
 def run(command,timeout=180):
  r=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
  if r.returncode:raise RuntimeError('Command failed: '+' '.join(command[:6])+' '+(r.stdout+r.stderr)[-600:])
  return r.stdout
 def healthy():
  name=project+'-marketing-a-1'
  for _ in range(60):
   try:
    data=json.loads(run(docker+['inspect',name]))[0]
    if data['State']['Health']['Status']=='healthy':return
   except RuntimeError:pass
   time.sleep(2)
  raise RuntimeError('A health did not recover')
 try:
  run(docker+['compose','-f',str(old_path),'-p',project,'up','-d','--no-deps','--force-recreate','marketing-a'])
  healthy();evidence['checks'].append('sealed-old-A-image-healthy-in-isolated-project')
  run(['node',str(ROOT/'docs/tests/td04-race.mjs'),'old-a',str(work)],60)
  if json.loads((work/'race-old-a-report.json').read_text())['status']!='PASSED':raise RuntimeError('Old A test failed')
  evidence['checks'].append('current-B-old-A-missing-RPC-explicit-503')
 finally:
  run(docker+['compose','-f',str(original),'-p',project,'up','-d','--no-deps','--force-recreate','marketing-a'])
  healthy()
 run(['node',str(ROOT/'docs/tests/td04-race.mjs'),'recovered',str(work)],60)
 evidence['checks'].append('current-A-restored-and-discovery-recovers')
 evidence.update(status='PASSED',generatedAt=datetime.datetime.now(datetime.timezone.utc).isoformat())
 (work/'old-a-compatibility-report.json').write_text(json.dumps(evidence,indent=2)+'\n')
 print('PASS TD04 old A compatibility in clone')
if __name__=='__main__':main()
