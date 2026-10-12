"""Build isolated B065 tools from pinned existing SDK/maintenance images. No runtime/secret mutation."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,os
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--java-home',required=True);a=p.parse_args()
 docker=['docker','--context','desktop-linux'];state=json.loads((ROOT/'.local/b06/control/state.json').read_text());result={}
 javac=Path(a.java_home)/'bin/javac.exe'
 for name,source,parent,deps,release in [('transport','FaultTransportProbe.java',state['sdkImage'],ROOT/'.local/b06/build/tools/libs','8'),('refund','RefundFaultProbe.java',state['maintenanceImage'],ROOT/'.local/b06/build/maintenance/libs','21')]:
  folder=ROOT/'.local/b06/build/fault-tools'/name;folder.mkdir(parents=True,exist_ok=True);classes=folder/'classes';classes.mkdir(exist_ok=True)
  subprocess.run([str(javac),'--release',release,'-proc:none','-cp',str(deps/'*'),'-d',str(classes),str(ROOT/'deploy/b06/verification'/source)],check=True)
  dockerfile='ARG PARENT\nFROM ${PARENT}\nCOPY classes/ /tools/classes/\n'
  if name=='refund':dockerfile+='ENTRYPOINT ["java","-Xmx192m","-Duser.home=/tmp","-cp","/tools/classes:/tools/libs/*","RefundFaultProbe"]\n'
  (folder/'Dockerfile').write_text(dockerfile);(folder/'.dockerignore').write_text('**\n!Dockerfile\n!classes/\n!classes/**\n')
  inputs={str(f.relative_to(folder)):hashlib.sha256(f.read_bytes()).hexdigest() for f in folder.rglob('*') if f.is_file()};fingerprint=hashlib.sha256(json.dumps({'inputs':inputs,'parent':parent},sort_keys=True).encode()).hexdigest()[:16];tag='zj-market-b06/fault-'+name+':'+fingerprint
  parent_tag='zj-market-b06/fault-parent:'+parent.split(':',1)[1]
  subprocess.run(docker+['tag',parent,parent_tag],check=True)
  assert json.loads(subprocess.check_output(docker+['image','inspect',parent_tag]))[0]['Id']==parent
  subprocess.run(docker+['build','--build-arg','PARENT='+parent_tag,'-t',tag,str(folder)],check=True)
  image=json.loads(subprocess.check_output(docker+['image','inspect',tag]))[0]
  result[name]={'id':image['Id'],'tag':tag,'parent':parent,'source':source,'sourceSha256':hashlib.sha256((ROOT/'deploy/b06/verification'/source).read_bytes()).hexdigest(),'inputs':inputs}
 (ROOT/'.local/b06/build/fault-tools/release.json').write_text(json.dumps(result,indent=2)+'\n');print('Fault tools built locally; ordinary images unchanged')
if __name__=='__main__':main()
