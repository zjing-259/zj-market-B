"""Call A's signed discovery RPC directly while B's public feature flag is off."""
from pathlib import Path
import hashlib,json,re,subprocess,zipfile

B=Path(__file__).resolve().parents[2]
WORK=B/'target/team-discovery/td05_20261015_01'
PROJECT='zj-market-td05-20261015-01'
DOCKER=['docker','--context','desktop-linux']
def call(args,stdin=None,timeout=180):
    r=subprocess.run([str(x) for x in args],input=stdin,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    if r.returncode:raise RuntimeError('TD05 direct RPC probe failed: '+' '.join(str(x) for x in args[:5])+' '+r.stderr[-600:])
    return r.stdout
def main():
    if 'b.team-discovery.enabled=false' not in (WORK/'private/config/b.properties').read_text(encoding='utf-8'):
        raise RuntimeError('Discovery must be off during direct A probe')
    release=json.loads((WORK/'release-manifest.json').read_text())
    jar=WORK/'build/b/app.jar'
    if hashlib.sha256(jar.read_bytes()).hexdigest().upper()!=release['artifacts']['b']['app.jar']:
        raise RuntimeError('B image input drift')
    probe=WORK/'rpc-probe';classes=probe/'classes';libs=probe/'lib'
    classes.mkdir(parents=True,exist_ok=True);libs.mkdir(parents=True,exist_ok=True)
    if not (probe/'extracted.ok').exists():
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                if name.startswith('BOOT-INF/classes/') and not name.endswith('/'):
                    rel=Path(name).relative_to('BOOT-INF/classes');target=classes/rel
                elif name.startswith('BOOT-INF/lib/') and name.endswith('.jar'):
                    target=libs/Path(name).name
                else:continue
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
        (probe/'extracted.ok').write_text(release['artifacts']['b']['app.jar'])
    else:
        if (probe/'extracted.ok').read_text()!=release['artifacts']['b']['app.jar']:raise RuntimeError('Stale probe classpath')
    java='C:/Program Files/Java/jdk-21/bin/javac.exe'
    call([java,'-cp',str(classes)+';'+str(libs/'*'),'-d',classes,B/'docs/tests/td05/Td05RpcProbe.java'])
    fixture=json.loads((WORK/'browser/fixture.json').read_text());goods=fixture['goods']['success'];activity=str(fixture['activities']['success']['activityId'])
    if not re.fullmatch('[a-f0-9-]{36}',goods) or not activity.isdigit():raise RuntimeError('Invalid fixture')
    sql=("SELECT CONCAT(o.user_id,' ',p.product_version) FROM zj_market_b06.b_market_order o "
         "JOIN zj_market_b06.b_product p ON p.goods_id=o.goods_id "
         f"WHERE o.goods_id='{goods}' AND o.business_status='GROUP_COMPLETED' LIMIT 1;")
    values=call(DOCKER+['exec','-i',PROJECT+'-mysql-1','sh','-c',
        'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names'],sql).strip().split()
    if len(values)!=2 or not re.fullmatch('[A-Za-z0-9._-]{1,64}',values[0]) or not values[1].isdigit():raise RuntimeError('No valid paid buyer fixture')
    base=json.loads((B/'deploy/b06/images.lock.json').read_text())['java21']
    command=DOCKER+['run','--rm','--network',PROJECT+'_rpc','--memory','384m','--read-only','--tmpfs','/tmp:rw,nosuid,size=64m',
      '--mount','type=bind,src='+str(probe)+',dst=/probe,readonly',
      '--mount','type=bind,src='+str(WORK/'private')+',dst=/private,readonly',
      '--entrypoint','java',base,'-Duser.home=/tmp','-cp','/probe/classes:/probe/lib/*',
      'cn.zj.zjmarket.td05.Td05RpcProbe',goods,activity,values[1],values[0]]
    output=call(command,timeout=120)
    if 'TD05_A_RPC_READY' not in output:raise RuntimeError('No real A RPC readiness marker')
    report={'stage':'TD-05','status':'PASSED_DIRECT_A_RPC_BEFORE_ENABLE','project':PROJECT,
      'bImageInputSha256':release['artifacts']['b']['app.jar'],'probeSourceSha256':hashlib.sha256((B/'docs/tests/td05/Td05RpcProbe.java').read_bytes()).hexdigest(),
      'result':next(line.strip() for line in output.splitlines() if 'TD05_A_RPC_READY' in line),
      'featureFlagDuringProbe':'false'}
    (WORK/'rpc-readiness-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS TD05 direct signed A RPC while B discovery is off')
if __name__=='__main__':main()
