"""Build an isolated replay probe and a distinct compatible packaging release from the pinned B065 image."""
from pathlib import Path
import json,hashlib,subprocess,argparse,importlib.util
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--java-home',required=True);a=p.parse_args();docker=['docker','--context','desktop-linux'];parent=json.loads((ROOT/'docs/b06-fault-release.json').read_text(encoding='utf-8'));home=ROOT/'.local/b06/build/recovery-tools';home.mkdir(parents=True,exist_ok=True);result={}
 for kind,base in [('replay',json.loads((ROOT/'.local/b06/control/state.json').read_text())['sdkImage']),('candidate',parent['images']['b'])]:
  context=home/kind;context.mkdir(exist_ok=True);tag='zj-market-b06/recovery-parent:'+base.split(':')[1];subprocess.run(docker+['tag',base,tag],check=True)
  assert json.loads(subprocess.check_output(docker+['image','inspect',tag]))[0]['Id']==base
  df='ARG PARENT\nFROM ${PARENT}\n'
  if kind=='replay':
   classes=context/'classes';classes.mkdir(exist_ok=True);subprocess.run([str(Path(a.java_home)/'bin/javac.exe'),'--release','8','-proc:none','-cp',str(ROOT/'.local/b06/build/tools/libs/*'),'-d',str(classes),str(ROOT/'deploy/b06/verification/RecoveryReplayProbe.java')],check=True);df+='COPY classes/ /tools/classes/\n'
  else:df+='LABEL cn.zj.market.release="b066-compatible-packaging" cn.zj.market.rollback.contract="V18-opaque-rosterVersion"\n'
  (context/'Dockerfile').write_text(df);(context/'.dockerignore').write_text('**\n!Dockerfile\n!classes/\n!classes/**\n');inputs={str(f.relative_to(context)):sha(f) for f in context.rglob('*') if f.is_file()};suffix=hashlib.sha256(json.dumps({'parent':base,'inputs':inputs},sort_keys=True).encode()).hexdigest()[:16];target='zj-market-b06/recovery-'+kind+':'+suffix
  subprocess.run(docker+['build','--build-arg','PARENT='+tag,'-t',target,str(context)],check=True);ident=json.loads(subprocess.check_output(docker+['image','inspect',target]))[0]['Id'];result[kind]={'id':ident,'parent':base,'tag':target,'inputs':inputs}
 assert result['candidate']['id']!=parent['images']['b'];result.update(schemaFingerprint=json.loads((ROOT/'.local/b06/control/state.json').read_text())['schemaFingerprint'],migrationHistoryHash=json.loads((ROOT/'.local/b06/control/state.json').read_text())['migrationHistoryHash'],businessJarSha256=parent['artifactSha256']['zj-market-app/target/zj-market-app-exec.jar'],protocol='V18-opaque-rosterVersion',rollbackImage=parent['images']['b']);(home/'release.json').write_text(json.dumps(result,indent=2)+'\n');print('RECOVERY_TOOLS_BUILT distinct candidate; original application unchanged')
if __name__=='__main__':main()
