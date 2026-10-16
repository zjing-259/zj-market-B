"""Verify new B's explicit failure against sealed old A in the TD05 clone."""
from pathlib import Path
import json,subprocess,time

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'target/team-discovery/td05_20261015_01'
PROJECT='zj-market-td05-20261015-01'
DOCKER=['docker','--context','desktop-linux']

def call(args,timeout=300):
    r=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=timeout)
    if r.returncode: raise RuntimeError('TD05 old-A check failed: '+' '.join(str(x) for x in args[:5]))
    return r.stdout

def main():
    path=WORK/'compose.json';config=json.loads(path.read_text(encoding='utf-8-sig'))
    release=json.loads((WORK/'release-manifest.json').read_text())
    old=json.loads((ROOT/'docs/b06-final-release.json').read_text())
    if config['name']!=PROJECT or config['services']['marketing-a']['image']!=release['images']['a']['id']:
        raise RuntimeError('Wrong TD05 A candidate')
    if call(DOCKER+['inspect','--format','{{.Image}}','zj-market-b06-marketing-a-1']).strip()!=old['images']['a']:
        raise RuntimeError('Historic A image drift')
    def save(): path.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    def deploy(): call(DOCKER+['compose','-p',PROJECT,'-f',path,'up','-d','--no-deps','--force-recreate','--wait','--wait-timeout','180','marketing-a'])
    report={'stage':'TD-05','status':'RUNNING','oldAImage':old['images']['a'],'newAImage':release['images']['a']['id'],'checks':[]}
    try:
        config['services']['marketing-a']['image']=old['images']['a'];save();deploy()
        call(['node',ROOT/'docs/tests/td05-release-gate.mjs',WORK,'old-a'],60)
        report['checks'].append('new-B-old-A-explicit-503')
    finally:
        config['services']['marketing-a']['image']=release['images']['a']['id'];save();deploy()
        for attempt in range(30):
            result=subprocess.run(['node',str(ROOT/'docs/tests/td05-release-gate.mjs'),str(WORK),'on'],capture_output=True,text=True,timeout=15)
            if result.returncode==0:break
            time.sleep(2)
        else:raise RuntimeError('Restored A remained unavailable to B after reconnect window')
        report['checks'].append('new-A-restored-live-discovery-200')
        report['status']='PASSED' if len(report['checks'])==2 else 'FAILED'
        (WORK/'old-a-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if report['status']!='PASSED':raise RuntimeError('TD05 old-A compatibility not complete')
    print('PASS TD05 old-A explicit 503 and restored new-A 200')

if __name__=='__main__':main()
