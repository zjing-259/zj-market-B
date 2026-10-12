"""Build isolated B06 SDK verification image; not part of runtime deployment."""
from pathlib import Path
import argparse,shutil,subprocess,json
ROOT=Path(__file__).resolve().parents[1]
def main(java_home,context):
 lock=json.loads((ROOT/'deploy/b06/images.lock.json').read_text());ctx=ROOT/'.local/b06/build/tools'
 (ctx/'libs').mkdir(parents=True,exist_ok=True);(ctx/'classes').mkdir(exist_ok=True)
 for f in (ROOT/'.local/b06/build/a-dependencies').glob('*.jar'):shutil.copyfile(f,ctx/'libs'/f.name)
 docker=['docker','--context',context]
 cid=subprocess.check_output(docker+['create','--network','none',lock['rocketmq']]).decode().strip()
 try:subprocess.run(docker+['cp',cid+':/home/rocketmq/rocketmq-4.9.7/lib/rocketmq-tools-4.9.7.jar',str(ctx/'libs/rocketmq-tools-4.9.7.jar')],check=True)
 finally:subprocess.run(docker+['rm',cid],check=True,capture_output=True)
 jc=Path(java_home)/'bin/javac.exe'
 if not jc.exists():jc=Path(java_home)/'bin/javac'
 subprocess.run([str(jc),'--release','8','-proc:none','-cp',str(ctx/'libs/*'),'-d',str(ctx/'classes'),str(ROOT/'deploy/b06/verification/SecurityProbe.java')],check=True)
 shutil.copyfile(ROOT/'deploy/b06/verification/Dockerfile',ctx/'Dockerfile');(ctx/'.dockerignore').write_text('**\n!Dockerfile\n!libs/\n!libs/**\n!classes/\n!classes/**\n')
 subprocess.run(docker+['build','--build-arg','BASE_IMAGE='+lock['java8'],'-t','zj-market-b06/security-tools:b061',str(ctx)],check=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--java-home',required=True);p.add_argument('--context',default='desktop-linux');a=p.parse_args();main(a.java_home,a.context)
