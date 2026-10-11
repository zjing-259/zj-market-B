"""Collect immutable B-05.3 evidence. Does not execute business work or rewrite old reports."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,zipfile,io,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(path,*args):return subprocess.check_output(['git','-C',str(path),*args],text=True).strip()
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);p.add_argument('--sql-batch',required=True);p.add_argument('--actual-batch',required=True);p.add_argument('--refund-actual-batch',required=True);p.add_argument('--regression-prefix',required=True);p.add_argument('--startup-batch',required=True);p.add_argument('--protected-after',required=True);a=p.parse_args()
 for k,v in vars(a).items():
  if k=='protected_after':continue
  if not re.fullmatch(r'[A-Za-z0-9-]+',v):p.error('Simple new batch names only')
 out=ROOT/'target/refund'/a.run_name;out.mkdir(parents=True,exist_ok=False)
 result={'stage':'B-05.3','status':'RUNNING','checks':[],'evidence':{},'scope':'simulated funds only; actual MySQL/channel/locks/two JVMs and fresh actual A eligibility; refund MQ/release/UI are later stages'}
 def check(name,yes):result['checks'].append({'name':name,'passed':bool(yes)})
 def report(label,path):
  raw=path.read_bytes();obj=json.loads(raw);result['evidence'][label]={'path':str(path),'sha256':hashlib.sha256(raw).hexdigest()};check(label,obj['status']=='PASSED');return obj
 def textreport(label,path):
  text=path.read_text(encoding='utf-8-sig');result['evidence'][label]={'path':str(path),'sha256':sha(path)};check(label,'status=PASSED' in text.splitlines());return text
 try:
  check('actual b-05 worktree',git(ROOT,'branch','--show-current')=='b-05' and git(ROOT,'rev-parse','HEAD')=='53ad32d222cdcb1b330cf07a53b2fd64e02ccccf')
  jar=ROOT/'zj-market-verification/target/zj-market-verification.jar';current=sha(jar);result['verificationJarSha256']=current
  sql=ROOT/'target/refund'/a.sql_batch;s=report('SQL/channel/locks/two JVMs',sql/'report.json');check('SQL same final package',s['verificationJarSha256'].lower()==current);check('SQL original protected rows unchanged',s['oldProtectedRowsMissingOrChanged']==0)
  for label in ['test','development']:
   text=textreport(label+' permissions',sql/(label+'-permissions.txt'));grants=[x for x in text.splitlines() if x.startswith('grant=GRANT SELECT, INSERT, UPDATE, DELETE ON ')]
   check(label+' exact 46-table DML',len(grants)==46 and all('flyway_schema_history' not in g for g in grants));check(label+' no DDL/history/A/system/grant','runtimeDDL/history/A/system/grant=DENIED' in text)
  textreport('refund verification',sql/'verify.txt');textreport('original request new JVM recovery',sql/'recover.txt')
  live=ROOT/'target/b03-readiness'/a.actual_batch;ar=report('fresh actual A reconciliation',live/'report.json');check('actual A caller/ports/default Java restored',all(ar.get(k) for k in ['environmentRestored','ownedPortsReleased','defaultJavaUnchanged']))
  provenance=dict(x.split('=',1) for x in (live/'provenance.txt').read_text(encoding='utf-8-sig').splitlines() if '=' in x);check('actual A same final B package',provenance['B-verification-jar-sha256'].lower()==current)
  check('original tested A runtime and contract',provenance['A-jar-sha256'].lower()=='223a02521120f6d83cb58220e7cff08839a5b6bcbac9bc5c00bca42f8e6c8392' and provenance['A-contract-sha256'].lower()=='83b02a7ebf5e80b5ef4d1b03936e6b1ca33eed32f6d9c68b451e855c6192d7dd')
  for mode in ['reconciliation','reconciliation-recover']:textreport('actual A '+mode,live/(mode+'.txt'))
  actual=ROOT/'target/refund'/a.refund_actual_batch;rf=report('actual A eligible refund with A stopped',actual/'report.json');check('actual refund same final package',rf['verificationJarSha256'].lower()==current);check('actual refund all other protected records unchanged',rf['oldProtectedRowsMissingOrChanged']==0);textreport('A stopped/RPC MQ disabled independent refund',actual/'actual.txt')
  for folder in ['payment-closing','settlement','fulfillment']:
   suffix={'payment-closing':'closing','settlement':'settlement','fulfillment':'fulfillment'}[folder]
   for mode in ['verify','recover']:textreport(folder+'/'+mode,ROOT/'target'/folder/(a.regression_prefix+'-'+suffix+'-regression')/(mode+'.txt'))
  baseline=json.loads((ROOT/'target/refund/b053-baseline/before.json').read_text(encoding='utf-8'))
  for path,h in baseline['files'].items():
   if '/db/migration/' in path.replace('\\','/') and path.endswith('.sql'):check('applied migration unchanged '+Path(path).name,sha(ROOT/path)==h)
  initial=set((ROOT/'target/refund/b053-20261011-01-sql/before-protected.txt').read_text(encoding='utf-8-sig').splitlines());protected=ROOT/a.protected_after;result['evidence']['final protected snapshot']={'path':str(protected),'sha256':sha(protected)};final=set(protected.read_text(encoding='utf-8-sig').splitlines());check('all pre-B053 funds/work/refund/HELD/guard/channel retained',initial<=final);result['originalProtectedRows']=len(initial);result['originalProtectedMissingOrChanged']=len(initial-final)
  main=Path('D:/Java/zj-market/docs/development-roadmap.md');b=json.loads((ROOT/'target/refund/b053-main-roadmap-boundary.json').read_text(encoding='utf-8'));raw=main.read_bytes();insert=(b['insertion']+'\n').encode();check('main roadmap unrelated bytes preserved',raw.count(insert)==1 and hashlib.sha256(raw.replace(insert,b'')).hexdigest()==b['beforeSha256'])
  check('B04 worktree unchanged',git(Path('D:/Java/zj-market-b-04'),'status','--porcelain')=='')
  external=json.loads((ROOT/'target/reconciliation/b052-external-a-state.json').read_text(encoding='utf-8'));a_root=Path('D:/Java/group-buy-market');check('A head and prior external config changes preserved',git(a_root,'rev-parse','HEAD')==external['head'] and git(a_root,'status','--porcelain')==external['status'].strip() and all(sha(a_root/f)==h for f,h in external['files'].items()));check('A contract unchanged',sha(a_root/'docs/ab-api-contract.md')==external['contractSha256'])
  counts={'tests':0,'failures':0,'errors':0,'skipped':0}
  for path in (ROOT/'zj-market-app/target/surefire-reports').glob('TEST-*.xml'):
   suite=ET.parse(path).getroot()
   for key in counts:counts[key]+=int(suite.attrib.get(key,0))
  result['junit']=counts;check('99 or more JUnit, all passing',counts['tests']>=99 and all(counts[k]==0 for k in ['failures','errors','skipped']))
  ordinary=ROOT/'zj-market-app/target/zj-market-app-exec.jar';startup=report('ordinary default startup',ROOT/'target/refund'/a.startup_batch/'report.json');check('ordinary startup same package and clean stop',startup['applicationJarSha256'].lower()==sha(ordinary) and startup['ownedProcessStopped'] and startup['defaultJavaUnchanged']);result['applicationJarSha256']=sha(ordinary)
  with zipfile.ZipFile(ordinary) as z:
   check('ordinary excludes Flyway/verification',not any('flyway' in n.lower() or 'verification' in n.lower() for n in z.namelist()))
   check('ordinary Java21 bytecode',int.from_bytes(z.read('BOOT-INF/classes/cn/zj/zjmarket/ZjMarketApplication.class')[6:8],'big')==65)
   contracts=[n for n in z.namelist() if re.search(r'/group-buy-market-contract-[^/]+\.jar$',n)];check('one unchanged Java8 A contract dependency',len(contracts)==1)
   if len(contracts)==1:
    with zipfile.ZipFile(io.BytesIO(z.read(contracts[0]))) as contract:
     classes=[n for n in contract.namelist() if n.endswith('.class')];check('A contract Java8 bytecode',bool(classes) and all(int.from_bytes(contract.read(n)[6:8],'big')==52 for n in classes))
   props=z.read('BOOT-INF/classes/application.properties').decode();check('new admission off, recovery on, scheduler on','b.refund.enabled=${B_REFUND_ENABLED:false}' in props and 'b.refund.recovery-enabled=${B_REFUND_RECOVERY_ENABLED:true}' in props and 'b.refund.scheduler-enabled=${B_REFUND_SCHEDULER_ENABLED:true}' in props)
  check('Git whitespace check',subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True).returncode==0)
  result['sourceSha256']={str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*.java') if 'target' not in p.parts};result['gitStatus']=git(ROOT,'status','--short');result['status']='PASSED' if all(c['passed'] for c in result['checks']) else 'FAILED'
 except Exception as e:result['status']='FAILED';result['errorType']=type(e).__name__;result['error']=str(e)
 (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('B-05.3 delivery: '+result['status']+'; '+str(out/'report.json'));return 0 if result['status']=='PASSED' else 1
if __name__=='__main__':raise SystemExit(main())
