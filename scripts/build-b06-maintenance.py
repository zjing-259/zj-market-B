from pathlib import Path
import argparse,json,zipfile,subprocess,shutil
ROOT=Path(__file__).resolve().parents[1]
def main(java_home,context):
 ctx=ROOT/'.local/b06/build/maintenance';ctx.mkdir(parents=True,exist_ok=True)
 for folder in ['libs','classes']:
  (ctx/folder).mkdir(exist_ok=True)
 with zipfile.ZipFile(ROOT/'zj-market-verification/target/zj-market-verification.jar') as z:
  for n in z.namelist():
   if n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):(ctx/'libs'/Path(n).name).write_bytes(z.read(n))
 jc=Path(java_home)/'bin/javac.exe'
 if not jc.exists():jc=Path(java_home)/'bin/javac'
 subprocess.run([str(jc),'--release','21','-proc:none','-cp',str(ctx/'libs/*'),'-d',str(ctx/'classes'),str(ROOT/'deploy/b06/init/DeploymentTool.java')],check=True)
 java=jc.parent/('java.exe' if jc.name.endswith('.exe') else 'java')
 subprocess.run([str(java),'-cp',str(ctx/'classes')+__import__('os').pathsep+str(ctx/'libs/*'),'DeploymentTool','selftest'],check=True)
 (ctx/'Dockerfile').write_text('ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nWORKDIR /tools\nCOPY libs/ /tools/libs/\nCOPY classes/ /tools/classes/\nUSER 10001:10001\nENTRYPOINT ["java","-XX:MaxRAMPercentage=50","-Duser.home=/tmp","-cp","/tools/classes:/tools/libs/*","DeploymentTool"]\n')
 (ctx/'.dockerignore').write_text('**\n!Dockerfile\n!libs/\n!libs/**\n!classes/\n!classes/**\n')
 base=json.loads((ROOT/'deploy/b06/images.lock.json').read_text())['java21']
 subprocess.run(['docker','--context',context,'build','--build-arg','BASE_IMAGE='+base,'-t','zj-market-b06/maintenance:b062',str(ctx)],check=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--java-home',required=True);p.add_argument('--context',default='desktop-linux');a=p.parse_args();main(a.java_home,a.context)
