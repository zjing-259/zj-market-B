"""Create fresh local-only B06 materials. Refuses overwrite/rotation; never prints secrets.
Requires cryptography, JDK keytool. CA keys stay under private/ and are never mounted.
"""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import argparse,ipaddress,json,secrets,subprocess,os
from cryptography import x509
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
ROOT=Path(__file__).resolve().parents[1]
def protect_windows(directory):
 if os.name!='nt':return
 # Restrict only the dedicated private directory; no repository/global ACL changes.
 # Native .NET avoids PSModulePath mixing between PowerShell 7 and Windows PowerShell.
 # Fail on any error and verify the effective DACL instead of trusting a zero shell exit.
 command="""$path=$args[0]; $ErrorActionPreference='Stop'; $acl=[System.IO.Directory]::GetAccessControl($path,[System.Security.AccessControl.AccessControlSections]::Access); $acl.SetAccessRuleProtection($true,$false); foreach($rule in @($acl.GetAccessRules($true,$false,[System.Security.Principal.SecurityIdentifier]))){$acl.RemoveAccessRuleSpecific($rule)}; $sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User; $allowed=@($sid,[System.Security.Principal.SecurityIdentifier]::new('S-1-5-18'),[System.Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')); foreach($identity in $allowed){$rule=[System.Security.AccessControl.FileSystemAccessRule]::new($identity,'FullControl','ContainerInherit,ObjectInherit','None','Allow');$acl.SetAccessRule($rule)}; [System.IO.Directory]::SetAccessControl($path,$acl); $actual=[System.IO.Directory]::GetAccessControl($path,[System.Security.AccessControl.AccessControlSections]::Access); if(-not $actual.AreAccessRulesProtected){throw 'PRIVATE_ACL_NOT_PROTECTED'}; foreach($rule in $actual.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier])){if($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Value -notin $allowed.Value){throw 'PRIVATE_ACL_UNEXPECTED_PRINCIPAL'}}"""
 # Pass path as a separate argument via a script file to avoid PowerShell interpolation.
 script=Path(directory)/'protect-materials.ps1';script.write_text(command.replace('$path=$args[0];','param([string]$path);'),encoding='utf-8')
 try:subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),str(directory)],check=True,capture_output=True)
 finally:script.unlink(missing_ok=True)
def main(directory,java_home):
 out=Path(directory).resolve()
 if out.exists(): raise ValueError('Materials directory already exists; preserve keys and use explicit reviewed rotation')
 out.mkdir(parents=True);protect_windows(out);priv=out/'private';priv.mkdir()
 def write(n,v): (out/n).write_text(v,encoding='utf-8')
 def key(): return rsa.generate_private_key(public_exponent=65537,key_size=2048)
 def savekey(n,k): (out/n).write_bytes(k.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
 def savecert(n,c): (out/n).write_bytes(c.public_bytes(serialization.Encoding.PEM))
 def cert(name,k,issuer,issuerkey,is_ca=False,sans=(),client=False):
  now=datetime.now(timezone.utc);subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)])
  b=x509.CertificateBuilder().subject_name(subject).issuer_name(issuer.subject if issuer else subject).public_key(k.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=365)).add_extension(x509.BasicConstraints(ca=is_ca,path_length=0 if is_ca else None),critical=True)
  b=b.add_extension(x509.KeyUsage(digital_signature=True,key_encipherment=not is_ca,key_cert_sign=is_ca,crl_sign=is_ca,content_commitment=False,data_encipherment=False,key_agreement=False,encipher_only=False,decipher_only=False),critical=True)
  if not is_ca:
   b=b.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH if client else ExtendedKeyUsageOID.SERVER_AUTH]),False)
  if sans:b=b.add_extension(x509.SubjectAlternativeName([x509.DNSName(s) for s in sans]),False)
  return b.sign(issuerkey or k,hashes.SHA256())
 def issue(name,sans=(),client=False):
  ck=key();ca=cert(name+'-ca',ck,None,None,True);savekey('private/'+name+'-ca-key.pem',ck);savecert(name+'-ca.pem',ca)
  k=key();c=cert(name,k,ca,ck,sans=sans,client=client);savekey(name+'-key.pem',k);savecert(name+'.pem',c)
  return ck,ca
 issue('web',['zj-market-ux.test']);issue('rpc-server',['marketing-a']);issue('rpc-client',client=True);issue('mysql',['mysql'])
 ck,ca=issue('mq',['namesrv','broker'])
 # Negative test: valid same-CA certificate that is not the pinned server leaf.
 k=key();savekey('private/mq-unpinned-key.pem',k);savecert('private/mq-unpinned.pem',cert('other-mq',k,ca,ck,sans=['namesrv','broker']))
 issue('untrusted',['marketing-a','namesrv','broker'])
 identity=key();savekey('identity-key.pem',identity);(out/'identity-public.pem').write_bytes(identity.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
 s={n:secrets.token_hex(32) for n in ['mysql_root','a_db','b_db','redis','mq_admin','mq_a','mq_b','rpc','msg_a','msg_b','truststore']}
 write('private/values.json',json.dumps(s))
 write('mysql-root',s['mysql_root']);write('redis-password',s['redis'])
 write('mysql-health.cnf','[client]\nuser=root\npassword='+s['mysql_root']+'\n')
 write('redis.conf','bind 0.0.0.0\nprotected-mode yes\nport 6379\nrequirepass '+s['redis']+'\nappendonly yes\nmaxmemory 128mb\nmaxmemory-policy noeviction\n')
 write('a.properties','spring.datasource.password='+s['a_db']+'\nspring.datasource.hikari.data-source-properties.trustCertificateKeyStorePassword='+s['truststore']+'\nredis.sdk.config.password='+s['redis']+'\nab.v2.rocketmq.secret-key='+s['mq_a']+'\nab.v2.rpc.secret='+s['rpc']+'\nab.v2.mq.a-secret='+s['msg_a']+'\nab.v2.mq.b-secret='+s['msg_b']+'\n')
 write('b.properties','b.infrastructure.database.password='+s['b_db']+'\nb.infrastructure.database.url=jdbc:mysql://mysql:3306/zj_market_b06?useUnicode=true&characterEncoding=utf8&serverTimezone=UTC&sslMode=VERIFY_IDENTITY&trustCertificateKeyStoreUrl=file:/run/secrets/mysql-trust.p12&trustCertificateKeyStoreType=PKCS12&trustCertificateKeyStorePassword='+s['truststore']+'\nb.infrastructure.mq.secret-key='+s['mq_b']+'\nb.infrastructure.rpc.secret='+s['rpc']+'\nb.infrastructure.mq.a-secret='+s['msg_a']+'\nb.infrastructure.mq.b-secret='+s['msg_b']+'\n')
 accounts=[('B06Admin','mq_admin',True,[],[]),('B06AppA','mq_a',False,['B_PRODUCT_EVENTS-b06=SUB','B_TRADE_EVENTS-b06=SUB','A_TEAM_EVENTS-b06=PUB','A_INTEGRATION_RESULTS-b06=PUB'],['A_PRODUCT_SYNC-b06=PUB|SUB','A_TRADE_FACTS-b06=PUB|SUB']),('B06AppB','mq_b',False,['B_PRODUCT_EVENTS-b06=PUB','B_TRADE_EVENTS-b06=PUB','A_TEAM_EVENTS-b06=SUB','A_INTEGRATION_RESULTS-b06=SUB'],['B_PRODUCT_SYNC_RESULTS-b06=PUB|SUB','B_INTEGRATION_RESULTS-b06=PUB|SUB','B_TEAM_EVENTS-b06=PUB|SUB'])]
 acl='globalWhiteRemoteAddresses: []\naccounts:\n'
 for access,sk,admin,topics,groups in accounts:
  acl+='  - accessKey: '+access+'\n    secretKey: '+s[sk]+'\n    admin: '+str(admin).lower()+'\n    defaultTopicPerm: '+('PUB|SUB' if admin else 'DENY')+'\n    defaultGroupPerm: '+('PUB|SUB' if admin else 'DENY')+'\n'
  for name,items in [('topicPerms',topics),('groupPerms',groups)]:
   if items: acl+='    '+name+':\n'+''.join('      - "'+v+'"\n' for v in items)
 write('plain_acl.yml',acl)
 write('private/truststore-password',s['truststore'])
 kt=Path(java_home)/'bin/keytool.exe'
 if not kt.exists():kt=Path(java_home)/'bin/keytool'
 subprocess.run([str(kt),'-importcert','-noprompt','-alias','mysql-b06','-file',str(out/'mysql-ca.pem'),'-keystore',str(out/'mysql-trust.p12'),'-storetype','PKCS12','-storepass:file',str(priv/'truststore-password')],check=True,capture_output=True)
 write('materials.json',json.dumps({'createdAt':datetime.now(timezone.utc).isoformat(),'purpose':'Dedicated B06 only; not imported/trusted automatically','certificates':[p.name for p in out.glob('*.pem') if 'key' not in p.name]},indent=2))
 print('Created private B06 materials; no values printed, no OS trust/network changes.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',default=str(ROOT/'.local/b06/runtime'));p.add_argument('--java-home',required=True);a=p.parse_args();main(a.directory,a.java_home)
