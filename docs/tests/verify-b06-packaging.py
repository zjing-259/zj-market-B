"""Verify actual image contents and static isolation invariants; no business DB operations."""
from pathlib import Path
import argparse,json,subprocess,hashlib,zipfile,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def main(context,run_name):
 work=ROOT/'.local/b06/packaging'/run_name
 if work.exists():raise ValueError('Use a fresh packaging run name')
 work.mkdir(parents=True)
 docker=['docker','--context',context];build=ROOT/'.local/b06/build'
 release=json.loads((build/'release-manifest.json').read_text());approved=json.loads((ROOT/'docs/b06-a-release-manifest.json').read_text());checks=[]
 def check(name,ok):
  if not ok:raise AssertionError(name)
  checks.append({'name':name,'status':'PASSED'})
 check('original-a-unchanged',sha(ROOT/approved['files'][0]['frozenPath'])==approved['files'][0]['sha256'])
 with zipfile.ZipFile(ROOT/approved['files'][0]['frozenPath']) as original,zipfile.ZipFile(build/'a/app.jar') as derived:
  check('a-no-environment-resources',not any(n.startswith('BOOT-INF/classes/application') and n.endswith(('.yml','.yaml','.properties')) for n in derived.namelist()))
  removed=set(release['inputs']['removedConfiguration']);replaced={'BOOT-INF/classes/cn/bugstack/config/RedisClientConfig.class'}
  check('a-unaffected-entries-byte-identical',all(original.read(n)==derived.read(n) for n in original.namelist() if n not in removed|replaced))
  for n in replaced|{'BOOT-INF/classes/cn/bugstack/config/LivenessController.class'}:
   check('a-overlay-java8-'+Path(n).stem,int.from_bytes(derived.read(n)[6:8],'big')==52)
  check('a-contract-unchanged',hashlib.sha256(derived.read('BOOT-INF/lib/group-buy-market-contract-1.0-SNAPSHOT.jar')).hexdigest().upper()==approved['embeddedContractSha256'])
 for service in ['a','b','web']:
  info=json.loads(subprocess.check_output(docker+['image','inspect',release['images'][service]['id']]))[0]
  check(service+'-linux-amd64',info['Os']=='linux' and info['Architecture']=='amd64')
  check(service+'-nonroot',info['Config']['User'] in ['10001:10001','101:101'])
  check(service+'-no-secret-env',not any(any(x in e.split('=',1)[0].lower() for x in ['password','secret','private_key']) for e in info['Config']['Env']))
  cid=subprocess.check_output(docker+['create','--network','none',release['images'][service]['id']]).decode().strip()
  try:
   if service!='web':
    target=work/(service+'.jar');subprocess.run(docker+['cp',cid+':/app/app.jar',str(target)],check=True,capture_output=True)
    check(service+'-image-input-hash',sha(target)==release['inputs']['derivedASha256' if service=='a' else 'bSha256'])
    with zipfile.ZipFile(target) as z:
     check(service+'-no-verification-flyway',not any('zj-market-verification' in n or 'flyway' in n.lower() for n in z.namelist()))
   else:
    target=work/'web';subprocess.run(docker+['cp',cid+':/usr/share/nginx/html',str(target)],check=True,capture_output=True)
    for f in (build/'web/dist').rglob('*'):
     if f.is_file():check('web-asset-'+f.relative_to(build/'web/dist').as_posix(),sha(f)==sha(target/f.relative_to(build/'web/dist')))
  finally:subprocess.run(docker+['rm',cid],check=True,capture_output=True)
 raw=subprocess.check_output(docker+['compose','--env-file',str(build/'release.env'),'-f',str(ROOT/'deploy/b06/compose.yml'),'config','--format','json'])
 compose=json.loads(raw);services=compose['services']
 check('only-web-published',all(not s.get('ports') for n,s in services.items() if n!='web') and services['web']['ports'][0]['published']=='443')
 check('windows-loopback-default',services['web']['ports'][0]['host_ip']=='127.0.0.1')
 check('private-networks-internal',all(compose['networks'][n]['internal'] for n in ['rpc','data','redis','mq']))
 check('no-external-networks-or-volumes',not any(x.get('external') for group in ['networks','volumes'] for x in compose[group].values()))
 check('no-private-ca-mounted',all('private/' not in x['file'].replace('\\','/') for x in compose['secrets'].values()))
 check('runtime-no-tools-service','tools' not in services and not any('verification' in s['image'] for s in services.values()))
 for n in ['marketing-a','market-b','web']:check(n+'-read-only-and-no-caps',services[n]['read_only'] and services[n]['cap_drop']==['ALL'])
 tests={'tests':0,'failures':0,'errors':0,'skipped':0}
 for f in (ROOT/'zj-market-app/target/surefire-reports').glob('TEST-*.xml'):
  e=ET.parse(f).getroot()
  for k in tests:tests[k]+=int(e.attrib.get(k,0))
 check('junit-regression',tests['tests']>=107 and not any(tests[k] for k in ['failures','errors','skipped']))
 check('frontend-built',(ROOT/'frontend/dist/index.html').exists())
 report={'status':'PASSED','runName':run_name,'checks':checks,'junit':tests,'release':release,'scope':'Image bytes, unchanged A entries/contract, network/secrets/ordinary-package invariants'}
 (work/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Packaging PASS: '+str(len(checks))+' checks; JUnit '+str(tests['tests']))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--context',default='desktop-linux');p.add_argument('--run-name',required=True);a=p.parse_args();main(a.context,a.run_name)
