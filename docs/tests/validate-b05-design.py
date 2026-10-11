"""B-05.1 design consistency checks, NOT a runtime refund acceptance suite.

Run from any directory with --run-name NEW_NAME. The first design run uses
the already captured target/b05-design/b051-20261010-01/before.json.
No database/network calls, no migration, no business data mutation.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'target/b05-design/b051-20261010-01'
checks = []


def check(name, condition, detail=None):
    checks.append({'name': name, 'passed': bool(condition), 'detail': detail})


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs)


def resolve(spec, reference):
    assert reference.startswith('#/'), reference
    value = spec
    for part in reference[2:].split('/'):
        value = value[part.replace('~1', '/').replace('~0', '~')]
    return value


def walk(value):
    yield value
    if isinstance(value, dict):
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def validate(spec, schema, value):
    """Small explicit subset used by the design; not a general JSON Schema engine."""
    if '$ref' in schema:
        return validate(spec, resolve(spec, schema['$ref']), value)
    if 'anyOf' in schema:
        return any(validate(spec, s, value) for s in schema['anyOf'])
    types = schema.get('type')
    if types:
        types = types if isinstance(types, list) else [types]
        matched = {'null': value is None, 'boolean': type(value) is bool,
                   'integer': type(value) is int, 'string': isinstance(value, str),
                   'object': isinstance(value, dict), 'array': isinstance(value, list)}
        if not any(matched[t] for t in types):
            return False
    if 'const' in schema and value != schema['const']:
        return False
    if 'enum' in schema and value not in schema['enum']:
        return False
    if isinstance(value, str):
        if len(value) < schema.get('minLength', 0) or len(value) > schema.get('maxLength', 10**9):
            return False
        if 'pattern' in schema and re.fullmatch(schema['pattern'], value) is None:
            return False
        if schema.get('format') == 'date-time':
            try:
                if datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is None:
                    return False
            except ValueError:
                return False
    if type(value) is int:
        if value < schema.get('minimum', value) or value > schema.get('maximum', value):
            return False
    if isinstance(value, list):
        if len(value) > schema.get('maxItems', 10**9):
            return False
        return all(validate(spec, schema['items'], x) for x in value)
    if isinstance(value, dict):
        props = schema.get('properties', {})
        if not set(schema.get('required', [])) <= value.keys():
            return False
        if schema.get('additionalProperties') is False and not value.keys() <= props.keys():
            return False
        return all(validate(spec, props[k], v) for k, v in value.items() if k in props)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', args.run_name):
        parser.error('unsafe run-name')
    out = ROOT / 'target/b05-design' / args.run_name
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / 'report.json'
    if report_path.exists():
        parser.error('report already exists; use a new run-name')
    try:
        run_checks()
    except Exception as error:
        check('validator execution', False, type(error).__name__ + ': ' + str(error))
    passed = all(c['passed'] for c in checks) and bool(checks)
    files = ['CONTEXT.md', 'docs/b05-joint-design.md', 'docs/b05-http-api.json',
             'docs/b05-development.md', 'docs/development-roadmap.md',
             'docs/session-handoff.md', 'docs/b04-b05-handoff.md', 'docs/tests/validate-b05-design.py']
    report = {'status': 'PASSED' if passed else 'FAILED', 'scope': 'B-05.1 static design only; no database/RPC/MQ/browser/refund runtime acceptance',
              'time': datetime.now(timezone.utc).isoformat(), 'checks': checks,
              'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'fingerprints': {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(report['status'] + ': ' + str(sum(c['passed'] for c in checks)) + '/' + str(len(checks)) + ' checks; ' + str(report_path))
    for c in checks:
        if not c['passed']:
            print('FAIL: ' + c['name'] + ' ' + str(c['detail']))
    raise SystemExit(0 if passed else 1)


def run_checks():
    spec = load(ROOT / 'docs/b05-http-api.json')
    design = (ROOT / 'docs/b05-joint-design.md').read_text(encoding='utf-8')
    process = (ROOT / 'docs/b05-development.md').read_text(encoding='utf-8')
    roadmap = (ROOT / 'docs/development-roadmap.md').read_text(encoding='utf-8')
    main_roadmap = Path('D:/Java/zj-market/docs/development-roadmap.md').read_text(encoding='utf-8')
    check('design-only OpenAPI3.1 and server/security', spec['openapi']=='3.1.0' and spec['x-design-status']=='design-only' and spec['servers']==[{'url':'/api/v1'}] and spec['security']==[{'BearerAuth':[]}])
    refs = [v['$ref'] for v in walk(spec) if isinstance(v, dict) and '$ref' in v]
    for reference in refs:
        resolve(spec, reference)
    check('all local schema/response references resolve', True, len(refs))
    expected = {('/orders/{orderId}/refund','get'),('/admin/refund-exceptions','get'),('/admin/refunds/{refundId}','get'),('/admin/refunds/{refundId}/controls','post'),('/admin/reconciliations','get'),('/admin/reconciliations/{taskId}','get')}
    actual = {(p,m) for p,v in spec['paths'].items() for m in v if m in ('get','post','put','delete','patch')}
    check('exact six operations, only controlled operator POST', actual==expected)
    ids=[]
    for path,method in sorted(actual):
        item=spec['paths'][path]; op=item[method]; ids.append(op['operationId'])
        check('role/design marker '+path, op['x-required-role']==('OPERATOR' if path.startswith('/admin/') else 'OWNER') and op['x-design-status']=='design-only' and 'security' not in op)
        params=item.get('parameters',[])+op.get('parameters',[])
        check('path parameters '+path, {p['name'] for p in params if p['in']=='path' and p.get('required')}==set(re.findall(r'\{([^}]+)\}',path)))
        check('auth/missing/error responses '+path, {'200','400','401','403','404','503'} <= op['responses'].keys())
        for resp in op['responses'].values():
            resp=resolve(spec,resp['$ref']) if '$ref' in resp else resp
            check('no-store and request id '+path+' '+method, resp['headers']['Cache-Control']['schema']['const']=='no-store' and 'X-Request-Id' in resp['headers'])
    check('unique operation IDs', len(ids)==len(set(ids)))
    schemas=spec['components']['schemas']
    for name,schema in schemas.items():
        if name.endswith('Response'):
            check('ApiResponse '+name, schema['required']==['code','message','data','requestId'] and schema.get('additionalProperties') is False)
    check('control exactly four required fields', schemas['RefundControlRequest']['required']==['operationId','action','expectedVersion','reason'] and schemas['RefundControlRequest']['properties']['action']['enum']==['CHECK','RETRY'])
    control=spec['x-examples']['control']
    check('positive control example', validate(spec,schemas['RefundControlRequest'],control))
    check('positive null owner refund example',validate(spec,schemas['OrderRefundViewResponse'],spec['x-examples']['noRefund']))
    for label,patch in [('force success',{'action':'SUCCEEDED'}),('force release',{'action':'RELEASE'}),('client amount',{'refundAmount':'1.00'}),('blank reason',{'reason':''}),('zero version',{'expectedVersion':'0'}),('numeric version',{'expectedVersion':3})]:
        check('negative HTTP '+label, not validate(spec,schemas['RefundControlRequest'],dict(control,**patch)))
    check('duplicate JSON keys rejected', rejects_duplicates())
    count=35; tables=[]
    for migration in spec['x-migration-plan']:
        count+=len(migration['tables']); tables+=migration['tables']
        check('migration table count V'+str(migration['version']),count==migration['runtimeTables'] and all(t in design for t in migration['tables']))
    check('planned new tables unique and no SQL applied',len(tables)==len(set(tables))==13 and count==48)
    for ident in spec['x-design-decisions']:
        rows=[next((line for line in doc.splitlines() if line.startswith('| '+ident+' ')),None) for doc in [roadmap,process,main_roadmap]]
        check('decision '+ident+' identical in process and both roadmaps',bool(rows[0]) and len(set(rows))==1)
    check('choices source and inherited identities', '用户授权' in process and 'B05-D1' in roadmap and 'B04-D7' in roadmap and 'refundId' in design and 'completionId' in design)
    # Local paths in NEW artifacts only; preserve historical cross-worktree paths.
    for filename in ['docs/b05-joint-design.md','docs/b05-development.md']:
        text=(ROOT/filename).read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if not target.startswith(('http:','https:','#')):
                check('document link '+filename+' '+target,(ROOT/filename).parent.joinpath(target.split('#')[0]).exists())
    # Design-level scenario oracle; does not call business code or simulate a DB.
    def complete(roster, decisions):
        return len(roster)==len(set(roster)) and len(decisions)==len(roster) and {x[0] for x in decisions}==set(roster) and all(x[1] in ('PAID_ACCEPTED','CLOSED_UNPAID','PAID_OUTSIDE_WINDOW') and x[2] for x in decisions)
    cases=[('full mixed', ['o1','o2','o3'], [('o1','PAID_ACCEPTED',True),('o2','CLOSED_UNPAID',True),('o3','PAID_OUTSIDE_WINDOW',True)], True),
           ('missing member',['o1','o2'],[('o1','PAID_ACCEPTED',True)],False),
           ('duplicate member',['o1','o2'],[('o1','PAID_ACCEPTED',True),('o1','CLOSED_UNPAID',True)],False),
           ('unknown',['o1'],[('o1','UNKNOWN',True)],False),
           ('unaccepted payment',['o1'],[('o1','PAID_ACCEPTED',False)],False),
           ('outside without persisted refund',['o1'],[('o1','PAID_OUTSIDE_WINDOW',False)],False),
           ('close without proof',['o1'],[('o1','CLOSED_UNPAID',False)],False)]
    for label,roster,results,want in cases:
        check('model exact roster '+label,complete(roster,results)==want)
    check('model payment window inclusive start/exclusive end', [100<=t<200 for t in [99,100,199,200]]==[False,True,True,False])
    def retry(status,eligible=True,conflict=False): return status=='FAILED' and eligible and not conflict
    for status in ['PENDING','UNKNOWN','SUCCEEDED','FAILED']:
        check('model retry '+status,retry(status)==(status=='FAILED'))
    check('model failed lacking eligibility never retry', not retry('FAILED',False))
    check('model evidence conflict never retry', not retry('FAILED',True,True))
    def full(paid,refund,prior): return Decimal(refund)==Decimal(paid)>0 and Decimal(prior)+Decimal(refund)<=Decimal(paid)
    for label,paid,refund,prior,want in [('full','10.00','10.00','0',True),('partial','10','9','0',False),('excess','10','11','0',False),('second full','10','10','10',False),('zero','0','0','0',False)]:
        check('model full refund '+label,full(paid,refund,prior)==want)
    def release(funds='SUCCEEDED',terminal=True,conflict=False,reservation='HELD',proof=True):
        if funds!='SUCCEEDED' or not terminal or conflict or not proof or reservation=='CONFIRMED': return 'WAIT'
        return 'ALREADY_RELEASED' if reservation=='RELEASED' else 'RELEASED'
    for label,patch,want in [('normal',{},'RELEASED'),('unknown',{'funds':'UNKNOWN'},'WAIT'),('failed',{'funds':'FAILED'},'WAIT'),('no terminal',{'terminal':False},'WAIT'),('fulfilled',{'reservation':'CONFIRMED'},'WAIT'),('conflict',{'conflict':True},'WAIT'),('already released',{'reservation':'RELEASED'},'ALREADY_RELEASED'),('missing old proof',{'reservation':'RELEASED','proof':False},'WAIT')]:
        check('model release '+label,release(**patch)==want)
    # A returns current version even when processing an older event. Require known local fact.
    known={1:'PENDING',2:'FAILED',3:'PENDING',4:'SUCCEEDED'}
    def receipt(version,status,current=4): return version in known and known[version]==status and version<=current
    check('model old event can report known newer success',receipt(4,'SUCCEEDED'))
    check('model same version other status rejected',not receipt(4,'FAILED'))
    check('model unknown higher version rejected',not receipt(5,'SUCCEEDED'))
    check('model old receipt cannot downgrade local high water',max(4,2)==4)
    check('terminal teams need not have frozen roster', 'RECONCILIATION_NOT_STARTED' in design and '不能要求它必须已有核对名单' in design)
    check('outside-window eligibility requires applied original submission', '单查FAILED不证明' in design and '原completionId原请求重放成功' in design and 'complete返回COMPLETED会跳过异常成员处理' in design)
    before=load(BASE/'before.json')
    mismatches=[path for path,digest in before['protected'].items() if not Path(path).exists() or hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest]
    check('all old Java/SQL/dependencies/HTTP and A contract unchanged',not mismatches,{'files':len(before['protected']),'mismatches':mismatches})
    current_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    check('branch/head unchanged',current_head==before['head'] and subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='b-05')
    diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    check('git diff whitespace',diff.returncode==0,diff.stdout+diff.stderr)
    check('source limitations explicitly documented','不返回closeId' in design and 'queryEventResult' in design and '冻结后不自动' in process and '静态模型检查不是' in design)
    boundary=load(BASE/'main-roadmap-boundary.json')
    check('main roadmap only authorized decision insertion',boundary['outsideInsertionUnchanged'] and hashlib.sha256(Path(boundary['mainPath']).read_bytes()).hexdigest()==boundary['afterSha'])
    allowed={'CONTEXT.md','docs/development-roadmap.md','docs/session-handoff.md','docs/b05-development.md','docs/tests/run-b05-baseline.ps1','docs/b05-joint-design.md','docs/b05-http-api.json','docs/b04-b05-handoff.md','docs/tests/validate-b05-design.py'}
    status=subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=ROOT,text=True)
    check('worktree changes confined to design and prior baseline entry',all(line[3:] in allowed for line in status.splitlines()),status.splitlines())


def rejects_duplicates():
    try:
        json.loads('{"action":"CHECK","action":"RETRY"}',object_pairs_hook=pairs)
    except ValueError:
        return True
    return False


if __name__=='__main__':
    main()
