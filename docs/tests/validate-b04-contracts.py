# Standard-library validator for this contract subset; not full OpenAPI conformance.
# Run after the corresponding fresh B-04 acceptance phases. No database or network access.
from pathlib import Path
from collections import Counter
import json,re,subprocess,copy,hashlib,zipfile,xml.etree.ElementTree as ET
import argparse
parser=argparse.ArgumentParser(description='B04 contract subset and delivery boundaries; requires fresh acceptance evidence')
parser.add_argument('--run-name',required=True);args=parser.parse_args();assert re.fullmatch('[A-Za-z0-9-]+',args.run_name)
root=Path(__file__).resolve().parents[2];work=root/'target/b04-acceptance'/args.run_name;assert work.is_dir()
import datetime
def git(*args):return subprocess.check_output(['git',*args],cwd=root).decode('utf-8')
def unique(pairs):
    d={}
    for k,v in pairs:
        assert k not in d,('duplicate JSON property',k)
        d[k]=v
    return d
api=json.loads((root/'docs/b04-http-api.json').read_text(encoding='utf-8'),object_pairs_hook=unique)
refs=[]
def resolve(ref):
    assert ref.startswith('#/'),ref
    v=api
    for key in ref[2:].split('/'):v=v[key.replace('~1','/').replace('~0','~')]
    return v
def walk(x):
    if isinstance(x,dict):
        for k,v in x.items():
            if k=='$ref':resolve(v);refs.append(v)
            if k=='pattern':re.compile(v)
            walk(v)
    elif isinstance(x,list):
        for v in x:walk(v)
walk(api)
checks=0
def validate(value,s):
    global checks
    checks+=1
    if '$ref' in s:s=resolve(s['$ref'])
    if 'oneOf' in s:
        count=0
        for alternative in s['oneOf']:
            try:validate(value,alternative);count+=1
            except (AssertionError,ValueError):pass
        assert count==1,('oneOf',value)
        return
    t=s.get('type');allowed=t if isinstance(t,list) else [t]
    types={'null':value is None,'string':isinstance(value,str),'boolean':type(value)is bool,'object':isinstance(value,dict),'array':isinstance(value,list),'integer':type(value)is int}
    assert t is None or any(types.get(a,False) for a in allowed),('type',value,t)
    if 'const' in s:assert type(value)==type(s['const']) and value==s['const']
    if 'enum' in s:assert value in s['enum']
    if isinstance(value,str):
        assert len(value)>=s.get('minLength',0) and len(value)<=s.get('maxLength',10**6)
        if 'pattern' in s:assert re.search(s['pattern'],value),('pattern',value,s['pattern'])
        if s.get('format')=='date-time':datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
    if isinstance(value,dict):
        assert set(s.get('required',[]))<=value.keys()
        if s.get('additionalProperties') is False:assert value.keys()<=s.get('properties',{}).keys()
        for key,v in value.items():
            if key in s.get('properties',{}):validate(v,s['properties'][key])
    if isinstance(value,list):
        if s.get('uniqueItems'):assert len(value)==len(set(json.dumps(x,sort_keys=True) for x in value))
        for x in value:validate(x,s.get('items',{}))
positive=negative=0;opids=[]
for path,item in api['paths'].items():
    params=re.findall(r'\{([^}]+)\}',path)
    assert {p['name'] for p in item['parameters']}==set(params)
    assert all(p['in']=='path' and p['required'] is True for p in item['parameters'])
    for method,op in item.items():
        if method=='parameters':continue
        opids.append(op['operationId']);assert set(op['responses'])>={'200','400','401','403','404','409','503'}
        if 'requestBody' not in op:continue
        assert method=='post' and '202' in op['responses']
        content=op['requestBody']['content']['application/json'];schema=content['schema']
        for ex in content['examples'].values():
            value=ex['value'];validate(value,schema);positive+=1
            for field in ['paidAt','amount','userId','fault','delayMillis','currency','teamStatus']:
                invalid=copy.deepcopy(value);invalid[field]='injected'
                try:validate(invalid,schema)
                except AssertionError:negative+=1
                else:raise AssertionError(('unexpected field accepted',field))
            invalid=copy.deepcopy(value);invalid.pop('operationId')
            try:validate(invalid,schema)
            except AssertionError:negative+=1
            else:raise AssertionError('missing operationId accepted')
assert len(opids)==len(set(opids))==6
for name,valid,invalid in [
 ('Money',['0.01','90.00','999999.99'],['90x00','90\\x00','090.00','90.0',90.0]),
 ('UtcMillis',['2026-10-10T03:00:00.123Z'],['2026-10-10T03:00:00x123Z','2026-10-10T03:00:00Z','2026-99-99T03:00:00.123Z']),
 ('ResultChoice',['SUCCEEDED','FAILED'],['UNKNOWN','CLOSED_UNPAID','PAID']),
 ('Id',['b041-op-1'],[' leading','trailing ','x'*65]),
]:
    for v in valid:validate(v,api['components']['schemas'][name]);positive+=1
    for v in invalid:
        try:validate(v,api['components']['schemas'][name])
        except (AssertionError,ValueError):negative+=1
        else:raise AssertionError(('invalid schema value accepted',name,v))

assert api['x-design-status']=='implemented-b04.6'
samples=json.loads((root/f'target/payments/{args.run_name}-payments/http-contract-samples.json').read_text(encoding='utf-8'))
for schema,value in samples.items():validate(value,api['components']['schemas']['OperationReceiptResponse' if schema=='choose-result' else schema])
paymentApi=api
api=json.loads((root/'docs/b03-http-api.json').read_text(encoding='utf-8'));api['components']['schemas']['Order']['properties']['status']['enum']=paymentApi['x-existing-order-extension']['statusEnum']
pv=copy.deepcopy(paymentApi['components']['schemas']['PaymentView']);props=pv['properties'];summaryKeys=['paymentId','fundsState','gate','aAcceptance','amount','currency','paidAt','allowedActions','reviewRequired','errorCode'];summary={**pv,'required':summaryKeys,'properties':{k:props[k] for k in summaryKeys}}
# Resolve payment refs before putting the summary into the original order contract namespace.
def expand(x):
 if isinstance(x,dict):
  if '$ref' in x:
   v=paymentApi
   for k in x['$ref'][2:].split('/'):v=v[k]
   return expand(v)
  return {k:expand(v) for k,v in x.items()}
 if isinstance(x,list):return [expand(v) for v in x]
 return x
api['components']['schemas']['Order']['properties']['paymentSummary']={'oneOf':[expand(summary),{'type':'null'}]};api['components']['schemas']['Order']['properties']['fulfillmentSummary']={'oneOf':[expand(paymentApi['components']['schemas']['FulfillmentSummary']),{'type':'null'}]}
orders=json.loads((root/f'target/payment-closing/{args.run_name}-payment-closing/http-contract-samples.json').read_text(encoding='utf-8'))
for name,value in orders.items():validate(value,api['components']['schemas']['OrderResponse'])
assert orders['exposed']['data']['canCancel'] is True
assert orders['closing']['data']['status']=='CLOSING' and not orders['closing']['data']['canCancel'] and not orders['closing']['data']['paymentEnabled']
assert orders['closed']['data']['status']=='CLOSED' and orders['closed']['data']['paymentSummary']['gate']=='CLOSED_UNPAID' and not orders['closed']['data']['canCancel']
for evidenceFile in [f'target/payments/{args.run_name}-fulfillment-browser/fulfillment-order-http.json',f'target/b03-readiness/{args.run_name}-live-fulfillment/fulfillment-order-http.json']:
 response=json.loads((root/evidenceFile).read_text(encoding='utf-8'));validate(response,api['components']['schemas']['OrderResponse']);assert response['data']['status']=='GROUP_COMPLETED' and response['data']['fulfillmentSummary']['status']=='PENDING';orders[evidenceFile]=response
api=paymentApi
summary=api['components']['schemas']['FulfillmentSummary'];good={'status':'PENDING','confirmedAt':'2026-10-10T08:00:00.123Z','paymentId':'pay-1','teamId':'team-1'};validate(good,summary)
for field,bad in [('status','SHIPPED'),('confirmedAt','2026-10-10T08:00:00Z'),('paymentId',' leading'),('teamId',None)]:
 changed={**good,field:bad}
 try:validate(changed,summary)
 except (AssertionError,ValueError):pass
 else:raise AssertionError(('fulfillment invalid accepted',field))

def git(*args):return subprocess.check_output(['git',*args],cwd=root).decode('utf-8')
baselineCommit='7cef24165a12fe443703142225c3dda5fd692a87'
for n in ['b02-http-api.json','b03-http-api.json']:assert git('show',baselineCommit+':docs/'+n).replace('\r\n','\n')==(root/'docs'/n).read_text(encoding='utf-8')
history={}
for p in (root/'zj-market-infrastructure/src/main/resources/db/migration').glob('V*.sql'):
 if re.match(r'V[1-9]__',p.name):
  rel=p.relative_to(root).as_posix();original=subprocess.check_output(['git','show',baselineCommit+':'+rel],cwd=root);assert original.decode('utf-8').replace('\r\n','\n')==p.read_text(encoding='utf-8');sha=hashlib.sha256(p.read_bytes()).hexdigest().upper();history[p.name]=sha
assert len(history)==9
assert hashlib.sha256((root.parent/'group-buy-market/docs/ab-api-contract.md').read_bytes()).hexdigest().upper()=='83B02A7EBF5E80B5EF4D1B03936E6B1CA33EED32F6D9C68B451E855C6192D7DD'
links=hashes=0
untracked=git('ls-files','--others','--exclude-standard').splitlines()
for n in git('diff','--name-only').splitlines()+untracked:
 if not n.endswith('.md'):continue
 p=root/n;s=p.read_text(encoding='utf-8');before='' if n in untracked else git('show','HEAD:'+n);h=Counter(re.findall(r'\b[0-9A-Fa-f]{64}\b',before));assert not h-Counter(re.findall(r'\b[0-9A-Fa-f]{64}\b',s)),n;hashes+=sum(h.values())
 pattern=r'(?<!!)\[[^\]]*\]\(([^)]+)\)'
 for target,count in (Counter(re.findall(pattern,s))-Counter(re.findall(pattern,before))).items():
  if re.match(r'^[a-zA-Z]+://',target):continue
  local=target.strip('<>').split('#')[0];assert not local or (p.parent/local).exists(),(n,target);links+=count
normal=root/'zj-market-app/target/zj-market-app-exec.jar'
with zipfile.ZipFile(normal) as z:assert not any('flyway' in n.lower() or 'verification' in n.lower() for n in z.namelist())
tests=failures=errors=skipped=0
for p in (root/'zj-market-app/target/surefire-reports').glob('TEST-*.xml'):
 t=ET.parse(p).getroot();tests+=int(t.attrib['tests']);failures+=int(t.attrib['failures']);errors+=int(t.attrib['errors']);skipped+=int(t.attrib['skipped'])
assert tests==77 and failures==errors==skipped==0
for scope in ['development','test']:
 permissions=(work/f'{scope}-permissions.txt').read_text(encoding='utf-8-sig')
 migration=(work/f'{scope}-migrate.txt').read_text(encoding='utf-8-sig')
 assert 'status=PASSED' in permissions and 'runtimeDDL/history/A/system/grant=DENIED' in permissions
 assert permissions.count('grant=GRANT SELECT, INSERT, UPDATE, DELETE ON ')==35
 assert 'status=PASSED' in migration and 'migrationsExecuted=0' in migration
result={'stage':'B-04.6','status':'PASSED','operations':len(opids),'schemas':len(api['components']['schemas']),'localRefs':len(refs),'schemaPositiveCases':positive,'schemaNegativeCases':negative,'actualPaymentHttpResponses':len(samples),'actualOrderHttpResponses':len(orders),'historicalMigrationsUnchanged':history,'V10ThroughV13':'validated by Flyway against both databases; no old migration rewrite','oldHttpContractsAndAContractUnchanged':True,'normalPackageExcludesFlywayAndVerification':True,'newLocalLinks':links,'historicalSha256OccurrencesPreserved':hashes,'JUnit':{'tests':tests,'failures':failures,'errors':errors,'skipped':skipped},'validator':'purpose-built validator for schema subset; original B03 OrderResponse extended in memory by B04 status/paymentSummary/fulfillmentSummary; not full OpenAPI conformance'}
(work/'contract-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='historicalMigrationsUnchanged'},ensure_ascii=False))
