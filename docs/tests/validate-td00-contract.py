"""TD-00 design/artifact checks; not live discovery RPC/HTTP acceptance."""
import argparse
import base64
import copy
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def unique(pairs):
    result = {}
    for k,v in pairs:
        if k in result: raise ValueError('duplicate key')
        result[k]=v
    return result


def canonical(o):
    return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def instant(s):
    if not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z',s): raise ValueError('time')
    return datetime.fromisoformat(s.replace('Z','+00:00'))


def fields(o):
    if isinstance(o,dict):
        for k,v in o.items():
            if k in ['activityId','productVersion','teamVersion']:
                if v is not None and (not isinstance(v,str) or not re.fullmatch('[1-9][0-9]*',v) or int(v)>9223372036854775807): raise ValueError('version')
            if k in ['source','channel','userId','goodsId','teamId','lastTeamId']:
                if not isinstance(v,str) or v.strip()!=v or not v or len(v.encode('utf-16-le'))//2>(8 if k in ['source','channel'] else 64): raise ValueError('id')
            if k in ['serverTime','validStartTime','validEndTime','lastEndTime'] and v is not None: instant(v)
            fields(v)
    elif isinstance(o,list):
        for x in o: fields(x)


def cursor(text,context,validator):
    if not re.fullmatch('[A-Za-z0-9_-]{1,1024}',text): raise ValueError('cursor encoding')
    raw=base64.b64decode(text+'='*((-len(text))%4),altchars=b'-_',validate=True)
    if len(raw)>768: raise ValueError('cursor bytes')
    o=json.loads(raw.decode('utf-8'),object_pairs_hook=unique)
    validator(o,'CursorPayload');fields(o)
    if base64.urlsafe_b64encode(canonical(o).encode()).decode().rstrip('=')!=text: raise ValueError('cursor canonical form')
    for key in ['source','channel','userId']:
        if o[key]!=context[key]: raise ValueError('0002')
    for key in ['goodsId','activityId','productVersion']:
        if o[key]!=context[key]: raise ValueError('TEAM_DISCOVERY_CONTEXT_CHANGED')
    return o


def page(o,request,validate):
    validate(o,'TeamDiscoveryPage');fields(o)
    for k in ['source','channel','userId','goodsId','activityId','productVersion']:
        if o[k]!=request[k]: raise ValueError('page context')
    if len(o['items'])>request['limit'] or o['hasMore']!=(o['nextCursor'] is not None): raise ValueError('page bounds')
    if o['hasMore'] and not o['items']: raise ValueError('empty more')
    if o['hasMore'] and len(o['items'])!=request['limit']: raise ValueError('short page with more')
    keys=[]
    for item in o['items']:
        if item['goodsId']!=o['goodsId'] or item['activityId']!=o['activityId']: raise ValueError('item context')
        if not (1<=item['paidCount']<=item['reservedCount']<item['targetCount']<=100): raise ValueError('counts')
        if not instant(item['validStartTime'])<=instant(o['serverTime'])<instant(item['validEndTime']): raise ValueError('time interval')
        keys.append((item['validEndTime'],item['teamId'].encode('utf-8')))
    if keys!=sorted(set(keys)) or len({i['teamId'] for i in o['items']})!=len(keys): raise ValueError('sort/duplicate')
    if o['hasMore']:
        c=cursor(o['nextCursor'],request,validate)
        if (c['lastEndTime'],c['lastTeamId'])!=(o['items'][-1]['validEndTime'],o['items'][-1]['teamId']): raise ValueError('cursor lookahead')


def main(args):
    sys.path.insert(0,str(args.schema_libs))
    from jsonschema import Draft202012Validator,FormatChecker
    from jsonschema.exceptions import ValidationError
    a=args.a_root
    spec=json.loads((a/'docs/schemas/team-discovery-v1.schema.json').read_text(encoding='utf-8'))
    vectors=json.loads((a/'docs/schemas/team-discovery-v1.examples.json').read_text(encoding='utf-8'))
    api=json.loads((ROOT/'docs/team-discovery-http-api.json').read_text(encoding='utf-8'))
    config=json.loads((ROOT/'docs/team-discovery-contract.json').read_text(encoding='utf-8'))
    checks=[]
    def check(name,work):
        work();checks.append(name)
    def validate(o,name):Draft202012Validator({'$ref':'#/$defs/'+name,'$defs':spec['$defs']},format_checker=FormatChecker()).validate(o)
    def valid_request(o):validate(o,'TeamDiscoveryRequest');fields(o)
    def rejected(name,work):
        try:work()
        except (ValueError,TypeError,KeyError,ValidationError):
            # jsonschema errors are checked here; no network/runtime failures hidden.
            checks.append('reject '+name);return
        raise AssertionError('accepted '+name)
    Draft202012Validator.check_schema(spec)
    check('request schema',lambda:valid_request(vectors['request']))
    check('page relations and cursor binds last returned item',lambda:page(vectors['page'],vectors['request'],validate))
    check('canonical cursor roundtrip',lambda:cursor(vectors['cursorEncoded'],vectors['request'],validate))
    assert hashlib.sha256(vectors['canonicalRequestJson'].encode()).hexdigest()==vectors['canonicalRequestSha256']
    checks.append('signing digest vector')
    for key,value in [('limit',0),('limit',11),('limit',True),('limit',3.5),('userId',' viewer'),('userId','viewer\n'),('userId','😀'*33),('activityId','01'),('activityId','9223372036854775808'),('productVersion','1\n'),('cursor',''),('source','x'*9)]:
        q={**vectors['request'],key:value};rejected(key+'='+repr(value),lambda q=q:valid_request(q))
    q={**vectors['request'],'userId':'CaseOwner'}
    rejected('cross user cursor',lambda:cursor(vectors['cursorEncoded'],q,validate))
    for key,value in [('source','other'),('channel','other'),('goodsId','other'),('activityId','714002'),('productVersion','2')]:
        q={**vectors['request'],key:value};rejected('cursor context '+key,lambda q=q:cursor(vectors['cursorEncoded'],q,validate))
    for value in [vectors['cursorEncoded']+'=', '@@@', 'A', base64.urlsafe_b64encode(b'{"cursorVersion":1,"cursorVersion":1}').decode().rstrip('='), base64.urlsafe_b64encode(b'\xff').decode().rstrip('='), 'A'*1025]:
        rejected('bad cursor syntax',lambda value=value:cursor(value,vectors['request'],validate))
    for key,value in [('cursorVersion',True),('sortVersion','OTHER'),('lastEndTime','2026-02-30T00:00:00.000Z'),('extra','x')]:
        c={**vectors['cursorPayload'],key:value};encoded=base64.urlsafe_b64encode(canonical(c).encode()).decode().rstrip('=');rejected('cursor payload '+key,lambda encoded=encoded:cursor(encoded,vectors['request'],validate))
    for key,value in [('paidCount',0),('paidCount',3),('reservedCount',3),('targetCount',101),('teamStatus','RECONCILING'),('goodsId','other'),('validEndTime',vectors['page']['serverTime']),('validStartTime','2026-10-14T00:31:00.000Z')]:
        p=copy.deepcopy(vectors['page']);p['items'][0][key]=value
        rejected('bad item '+key,lambda p=p:page(p,vectors['request'],validate))
    for mutation in ['duplicate','empty-more','wrong-next','privacy','over-limit']:
        p=copy.deepcopy(vectors['page'])
        if mutation=='duplicate':p['items']*=2
        if mutation=='empty-more':p['items']=[]
        if mutation=='wrong-next':p['items'][0]['teamId']='different'
        if mutation=='privacy':p['items'][0]['outTradeNo']='private'
        if mutation=='over-limit':p['items']*=4
        rejected(mutation,lambda p=p:page(p,vectors['request'],validate))
    http={'$defs':api['components']['schemas'],'$ref':'#/$defs/Success'}
    http=json.loads(json.dumps(http).replace('#/components/schemas/','#/$defs/'))
    hv=Draft202012Validator(http,format_checker=FormatChecker())
    def http_response(h):
        hv.validate(h);fields(h)
        d=h['data']
        for item in d['items']:
            if not 1<=item['paidCount']<=item['reservedCount']<item['targetCount']<=100:raise ValueError('HTTP counts')
            if item['availableSlots']!=item['targetCount']-item['reservedCount']:raise ValueError('HTTP availableSlots')
            if item['remainingPaidCount']!=item['targetCount']-item['paidCount']:raise ValueError('HTTP remainingPaidCount')
            if instant(d['serverTime'])>=instant(item['validEndTime']):raise ValueError('HTTP expired')
    http_response(vectors['httpSuccess']);checks.append('HTTP AVAILABLE example')
    for key,value in [('availableSlots',2),('remainingPaidCount',1),('paidCount',0),('validEndTime',vectors['page']['serverTime']),('outTradeNo','private')]:
        h=copy.deepcopy(vectors['httpSuccess']);h['data']['items'][0][key]=value
        rejected('HTTP '+key,lambda h=h:http_response(h))
    for state in ['ACTIVE_PURCHASE','UNAVAILABLE']:
        h=copy.deepcopy(vectors['httpSuccess']);d=h['data'];d.update(state=state,reason='INELIGIBLE' if state=='UNAVAILABLE' else None,activityId=None,serverTime=None,items=[],activeOrderId='own-order' if state=='ACTIVE_PURCHASE' else None,nextCursor=None,hasMore=False);hv.validate(h);checks.append('HTTP '+state)
        d['activityId']='714001';rejected(state+' activity privacy',lambda h=h:hv.validate(h))
    for name in ['TeamDiscoveryRequest','TeamDiscoveryPage','TeamDiscoveryItem']:
        source=(a/'group-buy-market-contract/src/main/java/cn/bugstack/api/v2'/f'{name}.java').read_text()
        actual=set(re.findall(r'private (?!static)[\w.<>]+ (\w+);',source))
        if name=='TeamDiscoveryRequest':actual|={'source','channel'}
        assert actual==set(spec['$defs'][name]['properties']),name
        checks.append(name+' Java/schema fields')
    assert api['paths']['/products/{goodsId}/joinable-teams']['get']['x-query-whitelist']==['limit','cursor']
    assert config['rpcTimeoutMillis']==3000 and config['overallBudgetMillis']==10000 and config['retries']==0
    checks.append('frozen timeout/query/role definitions')
    baseline=json.loads((args.baseline/'baseline.json').read_text(encoding='utf-8'))
    for name,root in [('a',a),('b',ROOT)]:
        for rel,expected in baseline['repositories'][name]['sourceSha256'].items():
            if name=='a' and rel in ['group-buy-market-contract/pom.xml','group-buy-market-contract/src/main/java/cn/bugstack/api/v2/V2Codes.java']:continue
            assert hashlib.sha256((root/rel).read_bytes()).hexdigest().upper()==expected,rel
    checks.append('all prior business Java, migration SQL and consumer dependencies unchanged')
    jar=a/'group-buy-market-contract/target/group-buy-market-contract-1.1.0-td.1.jar'
    lock=ROOT/'docs/team-discovery-contract-lock.json'
    if lock.exists():
        frozen=json.loads(lock.read_text(encoding='utf-8'))
        assert frozen['sha256']==hashlib.sha256(jar.read_bytes()).hexdigest().upper(), 'Frozen contract changed; use a new version'
        for rel,digest in frozen['aSourceSha256'].items():
            assert hashlib.sha256((a/rel).read_bytes()).hexdigest().upper()==digest,rel
        checks.append('immutable candidate hash and source lock')
    with zipfile.ZipFile(jar) as z:
        classes=[n for n in z.namelist() if n.endswith('.class')]
        assert len(classes)==40 and all(int.from_bytes(z.read(n)[6:8],'big')==52 for n in classes)
    checks.append('40 transport classes Java8 bytecode')
    result={'stage':'TD-00','status':'PASSED_CONTRACT_STATIC_CHECKS','checks':checks,'count':len(checks),'limits':['No discovery provider/HTTP implemented','No TLS/Triple discovery call, MQ or purchase acceptance performed']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.exists():raise ValueError('Fresh output required')
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'checks':len(checks),'output':str(args.output)}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--a-root',type=Path,required=True);p.add_argument('--schema-libs',type=Path,required=True)
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    main(p.parse_args())
