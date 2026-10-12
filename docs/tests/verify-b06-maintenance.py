"""Verify real maintenance-image bytes against ordinary B and original migration resources."""
from pathlib import Path
import argparse,json,zipfile,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[2]
def main(name,context):
 out=ROOT/'.local/b06/maintenance-integrity'/name
 if out.exists():raise ValueError('Use a fresh integrity run name')
 out.mkdir(parents=True)
 state=json.loads((ROOT/'.local/b06/control/state.json').read_text());docker=['docker','--context',context];image=state['maintenanceImage']
 cid=subprocess.check_output(docker+['create','--network','none',image]).decode().strip()
 try:
  subprocess.run(docker+['cp',cid+':/tools/classes/DeploymentTool.class',str(out/'DeploymentTool.class')],check=True,capture_output=True)
  subprocess.run(docker+['cp',cid+':/tools/libs',str(out/'libs')],check=True,capture_output=True)
 finally:subprocess.run(docker+['rm',cid],check=True,capture_output=True)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 assert sha(out/'DeploymentTool.class')==sha(ROOT/'.local/b06/build/maintenance/classes/DeploymentTool.class')
 checks=['actual-maintenance-image-class-equals-compiled-source']
 with zipfile.ZipFile(ROOT/'zj-market-app/target/zj-market-app-exec.jar') as b:
  for p in (out/'libs').glob('zj-market-*.jar'):
   if p.name.startswith('zj-market-app-'):
    with zipfile.ZipFile(p) as app:
     for n in b.namelist():
      if n.startswith('BOOT-INF/classes/') and not n.endswith('/'):
       name=n[len('BOOT-INF/classes/'):];assert app.read(name)==b.read(n),name
    checks.append('actual-tool-app-classes-and-resources-equal-runtime-b')
   else:
    name='BOOT-INF/lib/'+p.name;assert b.read(name)==p.read_bytes(),p.name;checks.append('actual-tool-runtime-shared-library-equal-'+p.name)
 infra=next((out/'libs').glob('zj-market-infrastructure-*.jar'))
 with zipfile.ZipFile(infra) as z:
  for p in (ROOT/'zj-market-infrastructure/src/main/resources/db/migration').glob('*.sql'):assert z.read('db/migration/'+p.name)==p.read_bytes(),p.name
 checks.append('actual-tool-all-19-original-migration-resources-equal-source')
 result=subprocess.run(docker+['run','--rm','--network','none','--memory','192m',image,'selftest'],capture_output=True,text=True,timeout=30)
 assert result.returncode==0 and 'DEPLOYMENT_PASS selftest' in result.stdout
 checks.append('actual-linux-image-sql-parser-selftest-under-192m')
 report={'status':'PASSED','image':image,'checks':checks,'classSha256':sha(out/'DeploymentTool.class'),'libraryHashes':{p.name:sha(p) for p in (out/'libs').glob('*.jar')}}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Maintenance integrity PASS',len(checks),'checks')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);p.add_argument('--context',default='desktop-linux');a=p.parse_args();main(a.run_name,a.context)
