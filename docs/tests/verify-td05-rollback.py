"""Exercise TD-05's isolated feature-off and certified B06 image fallback.

Only the named TD05 compose project is changed; restoration is in finally.
"""
from pathlib import Path
import hashlib, json, subprocess

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'target/team-discovery/td05_20261015_01'
PROJECT='zj-market-td05-20261015-01'
DOCKER=['docker','--context','desktop-linux']

def call(args,timeout=300):
    r=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=timeout,encoding='utf-8',errors='replace')
    if r.returncode: raise RuntimeError('TD05 rollback command failed: '+' '.join(str(x) for x in args[:5]))
    return r.stdout

def save(path,data): path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')

def main():
    compose=WORK/'compose.json'
    config=json.loads(compose.read_text(encoding='utf-8-sig'))
    release=json.loads((WORK/'release-manifest.json').read_text())
    old=json.loads((ROOT/'docs/b06-final-release.json').read_text())
    if config['name']!=PROJECT or config['services']['market-b']['image']!=release['images']['b']['id']:
        raise RuntimeError('Wrong TD05 candidate')
    if call(DOCKER+['inspect','--format','{{.Image}}','zj-market-b06-market-b-1']).strip()!=old['images']['b']:
        raise RuntimeError('Historic B06 image drift')
    prop=WORK/'private/config/b.properties'
    original=prop.read_text(encoding='utf-8')
    if 'b.team-discovery.enabled=true' not in original: raise RuntimeError('TD05 candidate not enabled')
    before=hashlib.sha256(compose.read_bytes()).hexdigest()
    report={'stage':'TD-05','status':'RUNNING','project':PROJECT,'checks':[],
            'candidateBImage':release['images']['b']['id'],'fallbackBImage':old['images']['b'],
            'composeBeforeSha256':before}
    save(WORK/'rollback-report.json',report)
    def deploy(): call(DOCKER+['compose','-p',PROJECT,'-f',compose,'up','-d','--force-recreate','--wait','--wait-timeout','180','market-b','web'])
    def gate(mode): call(['node',ROOT/'docs/tests/td05-release-gate.mjs',WORK,mode],60)
    try:
        prop.write_text(original.replace('b.team-discovery.enabled=true','b.team-discovery.enabled=false'),encoding='utf-8')
        deploy();gate('off');report['checks'].append('new-B-feature-disabled-route-404')
        config['services']['market-b']['image']=old['images']['b'];save(compose,config)
        deploy();gate('off');report['checks'].append('certified-B06-B-with-new-A-login-and-route-404')
        running=call(DOCKER+['inspect','--format','{{.Image}}',PROJECT+'-market-b-1']).strip()
        if running!=old['images']['b']:raise RuntimeError('Fallback image not running')
        report['checks'].append('fallback-image-id-exact')
    finally:
        config['services']['market-b']['image']=release['images']['b']['id'];save(compose,config)
        prop.write_text(original,encoding='utf-8')
        deploy();gate('on')
        report['checks'].append('new-B-restored-live-discovery-RPC-200')
        report['composeAfterSha256']=hashlib.sha256(compose.read_bytes()).hexdigest()
        report['status']='PASSED' if len(report['checks'])==4 else 'FAILED'
        save(WORK/'rollback-report.json',report)
    if report['status']!='PASSED':raise RuntimeError('TD05 rollback incomplete')
    print('PASS TD05 feature-off, old B image compatibility, candidate restore')

if __name__=='__main__':main()
