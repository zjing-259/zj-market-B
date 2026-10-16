"""Freeze current tracked and untracked A source, build TD-05 image contexts.

The old B-06 package and image contexts are never used as outputs.
"""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys

B = Path(__file__).resolve().parents[2]
A = Path('D:/Java/group-buy-market')
OUT = B / 'target/team-discovery/td05_20261015_01'
LOCK = json.loads((B/'deploy/b06/images.lock.json').read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def run(args, cwd=None):
    subprocess.run([str(x) for x in args], cwd=cwd, check=True)

def freeze_a():
    source = OUT/'a-source'
    source.mkdir(parents=True, exist_ok=False)
    names = subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'], cwd=A).split(b'\0')
    copied = {}
    for raw in names:
        if not raw: continue
        name = raw.decode('utf-8')
        if not (name == 'pom.xml' or name.startswith('group-buy-market-')): continue
        path = A/name
        if not path.is_file(): continue
        target = source/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path,target)
        copied[name] = sha(target)
    (OUT/'a-source-hashes.json').write_text(json.dumps(copied,indent=2)+'\n')
    run(['mvn.cmd','-o','-B','-DskipTests','package'],source)
    return source/'group-buy-market-app/target/group-buy-market-app.jar'

def context(key, app=None):
    p=OUT/'build'/key
    p.mkdir(parents=True,exist_ok=True)
    if key=='web':
        shutil.copytree(B/'frontend/dist',p/'dist')
        shutil.copyfile(B/'deploy/b06/nginx.conf',p/'nginx.conf')
        shutil.copyfile(B/'deploy/b06/images/web.Dockerfile',p/'Dockerfile')
    else:
        shutil.copyfile(app,p/'app.jar')
        shutil.copyfile(B/'deploy/b06/images/java.Dockerfile',p/'Dockerfile')
        run(['javac','-source','8','-target','8','-d',p,B/'deploy/b06/images/HealthProbe.java'])
    return p

def main():
    if OUT.exists() and not (OUT/'a-source-hashes.json').is_file():
        raise RuntimeError('Incomplete TD05 batch without frozen source')
    OUT.mkdir(parents=True,exist_ok=True)
    try:
        a_jar=(OUT/'a-source/group-buy-market-app/target/group-buy-market-app.jar')
        if not a_jar.is_file():
            if (OUT/'a-source-hashes.json').is_file():
                run(['mvn.cmd','-o','-B','-DskipTests','package'],OUT/'a-source')
            else:
                a_jar=freeze_a()
        b_jar=B/'zj-market-app/target/zj-market-app-exec.jar'
        if not b_jar.is_file(): raise RuntimeError('Build current B before TD05 packaging')
        if not (B/'frontend/dist/index.html').is_file(): raise RuntimeError('Build current web before TD05 packaging')
        manifest={'stage':'TD-05','status':'BUILDING','branch':{},'head':{},'artifacts':{},'images':{},'contractSha256':sha(B/'docs/team-discovery-contract.json')}
        for key,repo in [('a',A),('b',B)]:
            manifest['branch'][key]=subprocess.check_output(['git','branch','--show-current'],cwd=repo,text=True).strip()
            manifest['head'][key]=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
        for key,app in [('a',a_jar),('b',b_jar),('web',None)]:
            p=context(key,app)
            files={str(f.relative_to(p)).replace('\\','/'):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
            manifest['artifacts'][key]=files
            (OUT/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
            tag='zj-market-td05/'+key+':20261015-01'
            run(['docker','--context','desktop-linux','build','--platform','linux/amd64','--build-arg','BASE_IMAGE='+LOCK['java8' if key=='a' else 'java21' if key=='b' else 'web'],'-t',tag,p])
            inspect=json.loads(subprocess.check_output(['docker','--context','desktop-linux','image','inspect',tag]))[0]
            manifest['images'][key]={'tag':tag,'id':inspect['Id'],'base':LOCK['java8' if key=='a' else 'java21' if key=='b' else 'web']}
            (OUT/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        manifest['status']='BUILT_LOCAL_ONLY'
        (OUT/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    except Exception:
        raise

if __name__=='__main__': main()
