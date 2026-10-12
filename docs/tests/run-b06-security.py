"""B06.1 isolated transport/image checks. Uses dedicated project only, no shared DB.
The ordinary deployment is not initialized by this test. Failures remain in private run evidence.
"""
from pathlib import Path
import argparse,json,subprocess,time,os,hashlib
ROOT=Path(__file__).resolve().parents[2]
def main(run_name,context,keep):
 if not __import__('re').fullmatch(r'b061-[a-z0-9-]+',run_name):raise ValueError('Fresh B061 run name required')
 work=ROOT/'.local/b06/verification'/run_name
 if work.exists():raise ValueError('Never overwrite test evidence')
 work.mkdir(parents=True);secrets=ROOT/'.local/b06/runtime';build=ROOT/'.local/b06/build'
 project='zj-market-'+run_name;docker=['docker','--context',context]
 # Verification mounts only an allowlist: CA private keys never enter any container.
 import shutil
 test=work/'materials';test.mkdir()
 for name in ['rpc-server-ca.pem','rpc-client.pem','rpc-client-key.pem','mq.pem','web-ca.pem','untrusted-ca.pem','untrusted.pem','untrusted-key.pem']:
  shutil.copyfile(secrets/name,test/name)
 for name in ['mq-unpinned.pem','mq-unpinned-key.pem']:
  shutil.copyfile(secrets/'private'/name,test/name)
 values=json.loads((secrets/'private/values.json').read_text())
 (test/'probe.properties').write_text(''.join(k+'='+values[k]+'\n' for k in ['mq_admin','mq_a','mq_b','rpc']))
 compose=docker+['compose','-p',project,'--env-file',str(build/'release.env'),'-f',str(ROOT/'deploy/b06/compose.yml')]
 report={'runName':run_name,'project':project,'status':'RUNNING','checks':[],'scope':'Isolated security fixture; not full deployment/schema/business acceptance'}
 def run(name,args,stdin=None,expected=None,expected_exit=0):
  result=subprocess.run([str(x) for x in args],input=stdin,text=True,encoding='utf-8',errors='replace',capture_output=True,timeout=240)
  (work/(name+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
  if result.returncode!=expected_exit or (expected and expected not in result.stdout):raise RuntimeError(name+' failed; see private evidence')
  report['checks'].append({'name':name,'status':'PASSED'});(work/'progress.json').write_text(json.dumps(report,indent=2));print('PASS '+name,flush=True)
  return result.stdout
 def probe(name,kind,mode,wrong=False,tls_override=None):
  tls=tls_override or (work/'wrong-tls.properties' if wrong else ROOT/'deploy/b06/config/mq-tls-client.properties')
  return run(name,docker+['run','--rm','--network',project+('_mq' if kind=='mq' else '_rpc'),'--memory','320m','--mount','type=bind,src='+str(test)+',dst=/run/secrets,readonly','--mount','type=bind,src='+str(test)+',dst=/test,readonly','--mount','type=bind,src='+str(tls)+',dst=/etc/b06/mq-tls.properties,readonly','zj-market-b06/security-tools:b061',kind,mode],expected='PROBE_REJECTED' if mode in ['bad-secret','denied-topic','plaintext','bad-client','no-client','bad-ca','bad-pin'] else 'PROBE_PASS')
 try:
  run('compose-config',compose+['config','--quiet'])
  run('middleware-start',compose+['up','-d','--wait','--wait-timeout','150','mysql','redis','namesrv','broker'])
  mysql=project+'-mysql-1'
  root_cmd=['sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --skip-column-names']
  result=run('mysql-secure-config',docker+['exec','-i',mysql]+root_cmd,"SHOW VARIABLES LIKE 'require_secure_transport';\nSHOW VARIABLES LIKE 'ssl_cert';\n")
  if 'ON' not in result or '/run/secrets/mysql.pem' not in result:raise RuntimeError('MySQL TLS configuration ignored')
  values=json.loads((secrets/'private/values.json').read_text())
  # Empty disposable databases and runtime users only, no production/B business schema or money fixtures.
  sql="CREATE DATABASE IF NOT EXISTS group_buy_market_b06; CREATE USER IF NOT EXISTS 'a_runtime'@'%' IDENTIFIED BY '"+values['a_db']+"' REQUIRE SSL; GRANT SELECT,INSERT,UPDATE,DELETE ON group_buy_market_b06.* TO 'a_runtime'@'%';"
  run('empty-a-security-fixture',docker+['exec','-i',mysql]+root_cmd,sql)
  run('redis-auth-required',docker+['exec',project+'-redis-1','redis-cli','ping'],expected='NOAUTH')
  probe('mq-admin-topics','mq','init');probe('mq-route-vip-send-pull','mq','roundtrip');probe('mq-b-publish','mq','send')
  probe('mq-wrong-secret','mq','bad-secret');probe('mq-denied-topic','mq','denied-topic');probe('mq-plaintext-rejected','mq','plaintext')
  (work/'wrong-tls.properties').write_text('tls.test.mode.enable=false\ntls.client.authServer=true\ntls.client.trustCertPath=/run/secrets/untrusted-ca.pem\n')
  probe('mq-untrusted-ca','mq','bad-ca',True)
  # A second real NameServer has a different valid leaf signed by the same MQ CA.
  # Accepting its own leaf is the control; rejecting it with the deployed pin proves pinning.
  (work/'unpinned-tls.properties').write_text('tls.test.mode.enable=false\ntls.server.need.client.auth=none\ntls.server.authClient=false\ntls.server.keyPath=/test/mq-unpinned-key.pem\ntls.server.certPath=/test/mq-unpinned.pem\n')
  import yaml
  alt=work/'unpinned.yml';alt.write_text(yaml.safe_dump({'services':{'unpinned-namesrv':{'image':json.loads((ROOT/'deploy/b06/images.lock.json').read_text())['rocketmq'],'networks':['mq'],'mem_limit':'384m','entrypoint':['sh','-c'],'command':['exec java -Xmx192m -Duser.home=/tmp -Dtls.server.mode=enforcing -Dtls.test.mode.enable=false -Dtls.config.file=/etc/b06/tls.properties -cp "$$ROCKETMQ_HOME/conf:$$ROCKETMQ_HOME/lib/*" org.apache.rocketmq.namesrv.NamesrvStartup'],'volumes':[{'type':'bind','source':str(test),'target':'/test','read_only':True},{'type':'bind','source':str(work/'unpinned-tls.properties'),'target':'/etc/b06/tls.properties','read_only':True}],'healthcheck':{'test':['CMD-SHELL','bash -c "echo > /dev/tcp/127.0.0.1/9876"'],'interval':'2s','timeout':'2s','retries':20}}}},sort_keys=False))
  run('unpinned-namesrv-start',compose+['-f',str(alt),'up','-d','--no-deps','--wait','unpinned-namesrv'])
  (work/'unpinned-client.properties').write_text('tls.test.mode.enable=false\ntls.client.authServer=true\ntls.client.trustCertPath=/test/mq-unpinned.pem\n')
  probe('mq-other-leaf-positive-control','mq','pin-route',tls_override=work/'unpinned-client.properties')
  probe('mq-same-ca-unpinned-leaf-rejected','mq','bad-pin')
  run('a-container-start',compose+['up','-d','--no-deps','--wait','--wait-timeout','150','marketing-a'])
  encrypted=run('a-jdbc-encrypted-session',docker+['exec','-i',mysql]+root_cmd,"SELECT s.VARIABLE_VALUE FROM performance_schema.status_by_thread s JOIN performance_schema.threads t USING(THREAD_ID) WHERE t.PROCESSLIST_USER='a_runtime' AND s.VARIABLE_NAME='Ssl_cipher' AND s.VARIABLE_VALUE<>'';\n")
  if not encrypted.strip():raise RuntimeError('No encrypted A JDBC session observed')
  runtime_image=json.loads((build/'release-manifest.json').read_text())['baseImages']['java21']
  run('a-legacy-http-guard',docker+['run','--rm','--network',project+'_rpc','--memory','64m','--entrypoint','curl',runtime_image,'--silent','--show-error','--output','/tmp/body','--write-out','%{http_code}','-X','POST','--data','{}','-H','Content-Type: application/json','http://marketing-a:8080/api/v1/gbm/trade/lock-market-pay-order'],expected='403')
  probe('rpc-mtls-signed-validation','rpc','signed');probe('rpc-invalid-hmac','rpc','bad-hmac');probe('rpc-no-client-certificate','rpc','no-client');probe('rpc-untrusted-client','rpc','bad-client');probe('rpc-plaintext-rejected','rpc','plaintext')
  # Fixture B explicitly disables external capabilities; .2 supplies the real schema first.
  override=work/'fixture.yml';override.write_text('services:\n  market-b:\n    command:\n      - --spring.config.additional-location=file:/etc/b06/application.properties,file:/run/secrets/b.properties\n      - --b.infrastructure.database.enabled=false\n      - --b.identity.enabled=false\n      - --b.infrastructure.rpc.enabled=false\n      - --b.infrastructure.mq.enabled=false\n')
  fixture=compose+['-f',str(override)]
  run('b-web-container-start',fixture+['up','-d','--no-deps','--wait','--wait-timeout','120','market-b','web'])
  # Hostname/trust validation from a container using the same fixed runtime (curl present).
  image=json.loads((build/'release-manifest.json').read_text())['baseImages']['java21']
  def https(name,path,expected_code='200',ca='web-ca.pem'):
   return run(name,docker+['run','--rm','--network',project+'_edge','--memory','64m','--mount','type=bind,src='+str(test)+',dst=/run/secrets,readonly','--entrypoint','sh',image,'-c','curl --silent --show-error --cacert /run/secrets/'+ca+' --resolve zj-market.test:8443:$(getent hosts web | cut -d" " -f1) -o /tmp/body -w "%{http_code}" https://zj-market.test:8443'+path+'; cat /tmp/body'],expected=expected_code)
  https('https-health','/healthz');https('https-spa','/orders');https('https-api-404-not-spa','/api/b061-unknown','404');https('internal-health-not-public','/internal/health/live','404')
  for name,host,ca in [('https-wrong-ca','zj-market.test','untrusted-ca.pem'),('https-wrong-hostname','wrong.test','web-ca.pem')]:
   run(name,docker+['run','--rm','--network',project+'_edge','--memory','64m','--mount','type=bind,src='+str(test)+',dst=/run/secrets,readonly','--entrypoint','sh',image,'-c','curl --silent --show-error --cacert /run/secrets/'+ca+' --resolve '+host+':8443:$(getent hosts web | cut -d" " -f1) https://'+host+':8443/healthz'],expected_exit=60)
  if os.name=='nt':run('windows-host-https', ['node',ROOT/'docs/tests/b06-host-https.mjs',secrets/'web-ca.pem'],expected='HOST_HTTPS_PASS')
  report['status']='PASSED'
 except Exception as e:report['status']='FAILED';report['error']=str(e);raise
 finally:
  # Preserve container diagnostics before cleanup, including startup failures.
  if report['status']=='FAILED':
   diagnostics=subprocess.run(compose+['logs','--no-color','--tail','120'],capture_output=True,text=True)
   (work/'container-failure.log').write_text(diagnostics.stdout+diagnostics.stderr)
  # Only this project's containers/networks; volumes retained for diagnosis, never delete shared resources.
  if not keep:
   clean=subprocess.run(compose+['down','--remove-orphans'],capture_output=True,text=True)
   (work/'cleanup.log').write_text(clean.stdout+clean.stderr);report['cleanupExitCode']=clean.returncode
  report['images']=json.loads((build/'release-manifest.json').read_text())['images']
  (work/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print('B06 security: '+report['status'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);p.add_argument('--context',default='desktop-linux');p.add_argument('--keep',action='store_true');a=p.parse_args();main(a.run_name,a.context,a.keep)
