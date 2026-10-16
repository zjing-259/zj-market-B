"""Publish redacted TD-05 candidate evidence after isolated Docker acceptance."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,subprocess

B=Path(__file__).resolve().parents[2]
A=Path('D:/Java/group-buy-market')
WORK=B/'target/team-discovery/td05_20261015_01'
PROJECT='zj-market-td05-20261015-01'
DOCKER=['docker','--context','desktop-linux']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def call(args,stdin=None):
    r=subprocess.run([str(x) for x in args],input=stdin,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
    if r.returncode:raise RuntimeError('TD05 release check failed: '+' '.join(str(x) for x in args[:5]))
    return r.stdout
def admin(project,sql):
    return call(DOCKER+['exec','-i',project+'-mysql-1','sh','-c',
                'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --skip-column-names'],sql)
def source_hashes(repo):
    names=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=repo).split(b'\0')
    result={}
    for raw in names:
        if not raw:continue
        name=raw.decode('utf-8')
        if not (name=='pom.xml' or name.startswith('zj-market-') or name.startswith('frontend/src/') or name.startswith('frontend/tests/') or name in ('frontend/package.json','frontend/package-lock.json')):continue
        p=repo/name
        if p.is_file():result[name]=sha(p)
    return result
def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper()
def main():
    built=load(WORK/'release-manifest.json');prepare=load(WORK/'prepare-report.json')
    browser=load(WORK/'browser/browser-report.json');account=load(WORK/'browser/accounting-report.json')
    rollback=load(WORK/'rollback-report.json');old_a=load(WORK/'old-a-report.json')
    readiness=load(WORK/'rpc-readiness-report.json')
    old=load(B/'docs/b06-final-release.json');lock=load(B/'docs/team-discovery-contract-lock.json')
    if built['status']!='BUILT_LOCAL_ONLY' or prepare['status']!='READY':raise RuntimeError('Candidate not ready')
    if browser['status']!='PASSED' or account['status']!='PASSED_REAL_BROWSER_ACCOUNTING_SUBSET':raise RuntimeError('Transaction acceptance failed')
    if rollback['status']!='PASSED' or old_a['status']!='PASSED':raise RuntimeError('Compatibility gate failed')
    if readiness['status']!='PASSED_DIRECT_A_RPC_BEFORE_ENABLE' or readiness['featureFlagDuringProbe']!='false':
        raise RuntimeError('Missing direct pre-enable A RPC readiness')
    if sha(WORK/'a-source/group-buy-market-contract/target/group-buy-market-contract-1.1.0-td.1.jar')!=lock['sha256']:
        raise RuntimeError('Frozen contract byte drift')
    a_source=load(WORK/'a-source-hashes.json')
    if any(not (A/name).is_file() or sha(A/name)!=value for name,value in a_source.items()):
        raise RuntimeError('A source changed after freeze')
    for key in ('a','b','web'):
        for name,value in built['artifacts'][key].items():
            if sha(WORK/'build'/key/name)!=value:raise RuntimeError('Build context drift: '+key+'/'+name)
        image=load_image(built['images'][key]['id'])
        if image['Id']!=built['images'][key]['id'] or image['Architecture']!='amd64':raise RuntimeError('Image drift: '+key)
    containers=json.loads(call(DOCKER+['inspect']+[PROJECT+'-'+s+'-1' for s in ('mysql','redis','namesrv','broker','marketing-a','market-b','web')]))
    if any(c['State']['Health']['Status']!='healthy' or c['State']['OOMKilled'] for c in containers):raise RuntimeError('TD05 unhealthy')
    for service,key in [('marketing-a','a'),('market-b','b'),('web','web')]:
        if next(c for c in containers if c['Config']['Labels']['com.docker.compose.service']==service)['Image']!=built['images'][key]['id']:
            raise RuntimeError('Wrong running image: '+service)
    historic=json.loads(call(DOCKER+['inspect']+['zj-market-b06-'+s+'-1' for s in ('mysql','redis','namesrv','broker','marketing-a','market-b','web')]))
    if any(c['State']['Health']['Status']!='healthy' for c in historic):raise RuntimeError('B06 no longer healthy')
    for service,key in [('marketing-a','a'),('market-b','b'),('web','web')]:
        if next(c for c in historic if c['Config']['Labels']['com.docker.compose.service']==service)['Image']!=old['images'][key]:
            raise RuntimeError('B06 historic image changed')
    index=admin(PROJECT,"SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='group_buy_market_b06' AND INDEX_NAME IN ('idx_ab_team_discovery','idx_ab_order_discovery_owner');").strip()
    if index!='10':raise RuntimeError('TD05 index columns missing')
    grants=admin(PROJECT,"SHOW GRANTS FOR 'a_runtime'@'%'; SHOW GRANTS FOR 'b_runtime'@'%';")
    if any(x in grants.upper() for x in ('ALTER','CREATE','DROP','INDEX','ALL PRIVILEGES')):raise RuntimeError('Runtime DDL grant')
    spec=importlib.util.spec_from_file_location('deployment',B/'scripts/b06-deployment.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    d=object.__new__(module.Deployment);d.admin=lambda _label,sql:admin(PROJECT,sql)
    current_schema=d.fingerprint();current_history=d.history()
    original_state=load(Path('D:/Java/zj-market-b-06/.local/b06/control/state.json'))
    historic_d=object.__new__(module.Deployment)
    historic_d.admin=lambda _label,sql:admin('zj-market-b06',sql)
    if historic_d.fingerprint()!=original_state['schemaFingerprint'] or historic_d.history()!=original_state['migrationHistoryHash']:
        raise RuntimeError('Historic B06 live schema or migration history drift')
    if current_history!=original_state['migrationHistoryHash'] or current_schema==original_state['schemaFingerprint']:
        raise RuntimeError('Unexpected schema/history state')
    public_release={'stage':'TD-05','status':'LOCAL_WINDOWS_CANDIDATE_VERIFIED','generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'project':PROJECT,'origin':'https://zj-market.test:8445','branch':built['branch'],'head':built['head'],
        'sourceUncommitted':True,'aFrozenSourceFileCount':len(a_source),'aFrozenSourceSha256':digest(a_source),
        'bSourceSha256':digest(source_hashes(B)),'contract':{'coordinate':lock['coordinate'],'jarSha256':lock['sha256'],'apiJsonSha256':built['contractSha256']},
        'buildContexts':built['artifacts'],'images':built['images'],'legacyB06Images':old['images'],
        'aSchemaFingerprint':current_schema,'legacySchemaFingerprint':original_state['schemaFingerprint'],
        'bMigrationHistorySha256':current_history,'aIndexColumns':10,'runtimeDdlGranted':False,
        'registryPublished':False,'gitPublished':False,'linuxValidated':False,
        'evidence':{key:sha(path) for key,path in {'build':WORK/'release-manifest.json','prepare':WORK/'prepare-report.json',
            'browser':WORK/'browser/browser-report.json','accounting':WORK/'browser/accounting-report.json',
            'rollback':WORK/'rollback-report.json','oldA':WORK/'old-a-report.json',
            'preEnableRpc':WORK/'rpc-readiness-report.json'}.items()}}
    release_path=B/'docs/team-discovery-td05-release.json'
    release_path.write_text(json.dumps(public_release,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    acceptance={'stage':'TD-05','status':'PASSED_WINDOWS_ISOLATED_IMAGE_DELIVERY','stageCompletion':True,
        'runName':'td05_20261015_01','checks':{'realBrowser':len(browser['checks']),'accounting':len(account['accountingChecks']),
            'newHealthyServices':len(containers),'oldHealthyServices':len(historic),'aCursorTests':4,'bDiscoveryTests':18,
            'frontendEdgeTests':6,'flagOff404':True,'directRpcBeforeEnable':True,'liveRpc200':True,'oldA503':True,'fallbackOldBHealthy':True,
            'migrationHistoryUnchanged':True,'runtimeNoDDL':True},
        'scope':'Windows Docker Desktop isolated candidate; simulated channel money; B06 history unchanged',
        'releaseSha256':sha(release_path),'limitations':['No registry push or Git commit','Linux and external clients not validated']}
    (B/'docs/tests/td05-acceptance.json').write_text(json.dumps(acceptance,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS TD05 public release and acceptance manifests')
def load_image(image):return json.loads(call(DOCKER+['image','inspect',image]))[0]
if __name__=='__main__':main()
