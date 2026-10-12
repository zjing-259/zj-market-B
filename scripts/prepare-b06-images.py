"""Prepare allowlisted build contexts; never build the externally dirty A source tree.
Requires Python 3, JDK21, and already-built B/frontend artifacts. No private runtime files enter contexts.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, zipfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def run(args): subprocess.run([str(x) for x in args],check=True)
def prepare(java_home):
 manifest=json.loads((ROOT/'docs/b06-a-release-manifest.json').read_text())
 src=ROOT/manifest['files'][0]['frozenPath']
 if sha(src)!=manifest['files'][0]['sha256']: raise ValueError('A approved input hash mismatch')
 out=ROOT/'.local/b06/build';out.mkdir(parents=True,exist_ok=True)
 deps=out/'a-dependencies';deps.mkdir(exist_ok=True)
 classes=out/'overlay-classes';classes.mkdir(exist_ok=True)
 javac=Path(java_home)/'bin/javac.exe' if (Path(java_home)/'bin/javac.exe').exists() else Path(java_home)/'bin/javac'
 removed=[]
 with zipfile.ZipFile(src) as z:
  for n in z.namelist():
   if n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):
    (deps/Path(n).name).write_bytes(z.read(n))
  prop='BOOT-INF/classes/cn/bugstack/config/RedisClientConfigProperties.class'
  pp=deps/'classes/cn/bugstack/config/RedisClientConfigProperties.class';pp.parent.mkdir(parents=True,exist_ok=True);pp.write_bytes(z.read(prop))
 cp=str(deps/'*')+__import__('os').pathsep+str(deps/'classes')
 run([javac,'--release','8','-cp',cp,'-d',classes,*sorted((ROOT/'deploy/b06/a-overlay').glob('*.java'))])
 run([javac,'--release','8','-d',classes,ROOT/'deploy/b06/images/HealthProbe.java'])
 for service in ['a','b','web']:
  ctx=out/service;ctx.mkdir(exist_ok=True)
  # Only these named files are permitted; reject any unexpected stale context file.
  allowed={'app.jar','HealthProbe.class','Dockerfile','.dockerignore'} if service!='web' else {'dist','nginx.conf','Dockerfile','.dockerignore'}
  if any(x.name not in allowed for x in ctx.iterdir()): raise ValueError('Unexpected build context content')
  shutil.copyfile(ROOT/('deploy/b06/images/web.Dockerfile' if service=='web' else 'deploy/b06/images/java.Dockerfile'),ctx/'Dockerfile')
  (ctx/'.dockerignore').write_text('**\n!Dockerfile\n!app.jar\n!HealthProbe.class\n!dist/\n!dist/**\n!nginx.conf\n')
  if service!='web': shutil.copyfile(classes/'HealthProbe.class',ctx/'HealthProbe.class')
 a=out/'a/app.jar'
 with zipfile.ZipFile(src) as z,zipfile.ZipFile(a,'w') as target:
  for item in z.infolist():
   n=item.filename
   if n.startswith('BOOT-INF/classes/application') and n.endswith(('.yml','.yaml','.properties')):
    removed.append(n);continue
   if n=='BOOT-INF/classes/logback-spring.xml':
    removed.append(n);continue
   if n=='BOOT-INF/classes/cn/bugstack/config/RedisClientConfig.class':continue
   target.writestr(item,z.read(n))
  for f in sorted((classes/'cn').rglob('*.class')):
   info=zipfile.ZipInfo('BOOT-INF/classes/'+f.relative_to(classes).as_posix(),(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_STORED
   target.writestr(info,f.read_bytes())
 b=ROOT/'zj-market-app/target/zj-market-app-exec.jar';shutil.copyfile(b,out/'b/app.jar')
 with zipfile.ZipFile(b) as z:
  if any('flyway' in n.lower() or 'zj-market-verification' in n for n in z.namelist()): raise ValueError('Ordinary B contains forbidden tools')
 shutil.copytree(ROOT/'frontend/dist',out/'web/dist',dirs_exist_ok=True)
 # Reject stale dist files left from an earlier build.
 expected={f.relative_to(ROOT/'frontend/dist') for f in (ROOT/'frontend/dist').rglob('*') if f.is_file()}
 actual={f.relative_to(out/'web/dist') for f in (out/'web/dist').rglob('*') if f.is_file()}
 if expected!=actual: raise ValueError('Stale frontend context; use a fresh isolated build directory')
 shutil.copyfile(ROOT/'deploy/b06/nginx.conf',out/'web/nginx.conf')
 record={'originalASha256':sha(src),'derivedASha256':sha(a),'bSha256':sha(b),'removedConfiguration':removed,
 'overlaySources':{f.relative_to(ROOT).as_posix():sha(f) for f in sorted((ROOT/'deploy/b06/a-overlay').glob('*.java'))},
 'aSourceBuildClaim':False,'changes':'Remove all application profiles and old logging config; replace Redis config with password-required equivalent; add internal liveness only',
 'contexts':{svc:{f.relative_to(out/svc).as_posix():sha(f) for f in sorted((out/svc).rglob('*')) if f.is_file()} for svc in ['a','b','web']}}
 (out/'artifact-manifest.json').write_text(json.dumps(record,indent=2)+'\n')
 print('Prepared A/B/web contexts; original A preserved; derived hashes recorded.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--java-home',required=True);prepare(p.parse_args().java_home)
