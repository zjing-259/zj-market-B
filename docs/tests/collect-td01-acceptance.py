"""Read-only TD01 final audit and sanitized evidence index. No service/data writes."""
import argparse,hashlib,json,re,subprocess,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def main(args):
    a=args.a_root;work=args.work.resolve();r=read(work/'report.json')
    assert r['status']=='PASSED_A_DISCOVERY_REAL_MYSQL_TLS' and all(r['checks'].values())
    assert r['originalFinancialBefore']==r['originalFinancialAfter']
    lock=read(ROOT/'docs/team-discovery-contract-lock.json')
    installed=Path.home()/'.m2/repository/cn/bugstack/group-buy-market-contract/1.1.0-td.1/group-buy-market-contract-1.1.0-td.1.jar'
    assert sha(installed)==r['contractJarSha256']==lock['sha256']
    assert sha(a/'group-buy-market-app/target/group-buy-market-app.jar')==r['appJarSha256']==sha(work/'tested-app.jar')
    for rel,digest in lock['aSourceSha256'].items():assert sha(a/rel)==digest,rel
    baseline=read(ROOT/'target/team-discovery/td00-20261014-02/baseline.json')
    intentional={'pom.xml','group-buy-market-contract/pom.xml','group-buy-market-contract/src/main/java/cn/bugstack/api/v2/V2Codes.java',
                 'group-buy-market-app/src/main/java/cn/bugstack/v2/V2MarketingEngine.java','group-buy-market-app/src/main/java/cn/bugstack/v2/V2Security.java'}
    intentional|={'group-buy-market-app/src/test/java/cn/bugstack/test/v2/'+n+'.java' for n in ['V2PaymentFlowTest','V2ProductEventTest','V2MarketingContractTest','V2OutboxRecoveryTest']}
    protected_counts={}
    for name,root in [('a',a),('b',ROOT)]:
        n=0
        for rel,digest in baseline['repositories'][name]['sourceSha256'].items():
            if name=='a' and rel in intentional:continue
            assert sha(root/rel)==digest,rel;n+=1
        protected_counts[name]=n
    docker=['docker','--context','desktop-linux'];owner=r['runName']
    def cmd(parts):return subprocess.check_output(docker+parts,text=True,encoding='utf-8',timeout=30).strip()
    assert not cmd(['ps','-a','--filter','label=td01.owner='+owner,'--format','{{.Names}}'])
    assert not cmd(['network','ls','--filter','label=td01.owner='+owner,'--format','{{.Name}}'])
    expected=read(ROOT/'docs/b06-final-release.json')['allRuntimeImages']
    containers=json.loads(cmd(['inspect']+['zj-market-b06-'+s+'-1' for s in expected]))
    healthy={x['Config']['Labels']['com.docker.compose.service']:{'image':x['Image'],'running':x['State']['Running'],'health':x['State'].get('Health',{}).get('Status')} for x in containers}
    assert all(healthy[s]['image']==v and healthy[s]['running'] and healthy[s]['health']=='healthy' for s,v in expected.items())
    test_counts={}
    for label in ['discovery-unit','legacy-v2','live-tls']:
        log=(work/(label+'.log')).read_text(encoding='utf-8')
        m=re.search(r'OK \((\d+) tests?\)',log);assert m,label
        test_counts[label]=int(m.group(1))
    native=0
    for name in ['V2TeamDiscoveryCursorTest','V2AuthorizationTest','V2TlsGateTest','V2SecurityVectorTest']:
        p=a/('group-buy-market-app/target/surefire-reports/TEST-cn.bugstack.test.v2.'+name+'.xml');suite=ET.parse(p).getroot()
        assert not any(int(suite.get(k,'0')) for k in ['failures','errors','skipped']);native+=int(suite.get('tests'))
    paths=[work/'report.json',work/'tested-app.jar',work/'explain.txt',work/'explain-analyze.txt',work/'live-metrics.json']+[work/(s+'.log') for s in test_counts]
    migration=a/'docs/dev-ops/mysql/sql/migrations/20261014-team-discovery.sql'
    code=[a/'pom.xml',migration,a/'docs/tests/run-team-discovery.py']
    code+=sorted((a/'group-buy-market-app/src/main/java/cn/bugstack/v2').glob('V2TeamDiscovery*.java'))
    code+=[a/'group-buy-market-app/src/main/java/cn/bugstack/v2/V2MarketingEngine.java',a/'group-buy-market-app/src/main/java/cn/bugstack/v2/V2Security.java']
    code+=sorted((a/'group-buy-market-app/src/test/java/cn/bugstack/test/v2').glob('*.java'))
    release={'stage':'TD-01','status':'TESTED_A_CANDIDATE_NOT_DEPLOYED','generatedAt':datetime.now(timezone.utc).isoformat(),
             'aHead':subprocess.check_output(['git','-C',str(a),'rev-parse','HEAD'],text=True).strip(),
             'branch':subprocess.check_output(['git','-C',str(a),'branch','--show-current'],text=True).strip(),
             'sourceUncommitted':True,'aJarSha256':r['appJarSha256'],'artifactPath':str(work/'tested-app.jar'),
             'contract':{'coordinate':lock['coordinate'],'sha256':lock['sha256'],'locallyInstalled':True,'remotePublished':False},
             'migration':{'path':migration.relative_to(a).as_posix(),'sha256':sha(migration),'originalB06Applied':False,'requiredBeforeNewDiscoveryUse':True},
             'sourceSha256':{p.relative_to(a).as_posix():sha(p) for p in code},
             'runtimeDeploymentUpdated':False,'bConsumerUpdated':False,'discoverySqlRequiresIndexes':['idx_ab_team_discovery','idx_ab_order_discovery_owner']}
    summary={'stage':'TD-01','status':'PASSED_A_QUERY_SECURITY_AND_ISOLATED_ACCEPTANCE','stageCompletion':True,
             'generatedAt':release['generatedAt'],'runName':owner,'checks':r['checks'],'junit':{'docker':test_counts,'dockerTotal':sum(test_counts.values()),'failures':0,'errors':0,'nativeBuildChecks':native,'nativeNotAddedToTotal':'Repeated cursor/auth/TLS/vector subset overlaps final Docker suites'},
             'sqlTiming':r['sqlTiming'],'rpcTiming':r['latency'],'schemas':r['schemas'],
             'actualPlan':'Both TD indexes used; candidate index visited 12 rows for LIMIT 11. Former unforced plan in failed batch03 visited 2012.',
             'permissionScope':'SSL-required runtime users: DML only on isolated A business tables; no DDL/original A/mysql.user access',
             'originalFinancialBefore':r['originalFinancialBefore'],'originalFinancialAfter':r['originalFinancialAfter'],
             'originalFinancialUnchanged':True,'originalServices':healthy,'temporaryContainersAndNetworkRemoved':True,
             'oldSourceProtection':protected_counts,'frozenContractSourcesUnchanged':True,'localContractPublicationVerified':True,
             'artifact':release['aJarSha256'],'contract':release['contract'],'migration':release['migration'],
             'evidence':{p.relative_to(a).as_posix():sha(p) for p in paths},
             'previousBatches':{'td01_20261014_01':'FAILED test classpath empty entry; only accidental generated classes copy removed, failed report retained',
                                'td01_20261014_02':'FAILED live test ApplicationConfig collision; new DB tests and 44 old V2 tests passed',
                                'td01_20261014_03':'FAILED actual index selection gate; 13 unit +44 legacy+11 TLS passed; optimizer used old broad index'},
             'limitations':['Not actual B HTTP/UI or deployment acceptance; TD02-05 pending','Live TLS uses production beans in explicit test wiring with real MySQL/MyBatis/discounts/Redis; no MQ/scheduler workers started',
                            'Payment compatibility runs the real event engine directly; not a new MQ transport acceptance',
                            'Performance dataset has synthetic candidate counts; separate actual reserve/payment fact proves unpaid hidden then accepted payment visible',
                            'SQL p95 uses 20 EXPLAIN ANALYZE root-iterator samples; RPC p95 uses 20 sequential signed TLS calls; no HTTP/QPS/HA SLA',
                            'Isolated A schemas cloned from actual DDL then new index migration applied; no B Flyway runtime certification',
                            'Original B06 DB did not receive new indexes and old A/B/web images remain pinned','Combined cursor UTF8 payload over 768 bytes fails 0002; never returns an overlong unusable cursor'],
             'gitPublished':False,'nextStage':'TD-02'}
    for path,document in [(ROOT/'docs/team-discovery-a-release.json',release),(ROOT/'docs/tests/td01-acceptance.json',summary)]:
        if path.exists():raise ValueError('Keep historical evidence; use a new named output')
        path.write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':summary['status'],'dockerTests':sum(test_counts.values()),'sqlP95Millis':r['sqlTiming']['p95Millis'],'rpcP95Millis':r['latency']['rpcP95Millis'],'originalHealthy':True,'temporaryResourcesRemoved':True}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--a-root',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    main(p.parse_args())
