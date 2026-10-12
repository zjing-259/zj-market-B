"""Seal and verify a public source/evidence ZIP; never include local secrets or images."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, subprocess, zipfile, re
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
HOME=ROOT/'.local/b06/delivery'
EXCLUDED={'.local','.git','target','node_modules','dist','__pycache__','.codex','.agents'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,message):
 if not ok:raise RuntimeError(message)
def safe(name):
 p=PurePosixPath(name)
 return not p.is_absolute() and '..' not in p.parts and not EXCLUDED.intersection(p.parts) and ':' not in name and '\\' not in name and p.suffix.lower() not in {'.pem','.key','.p12','.pfx','.jks','.jar','.tar','.zip','.pyc'} and '.env' not in p.parts
def verify(directory):
 d=Path(directory);m=json.loads((d/'manifest.json').read_text(encoding='utf-8'));done=json.loads((d/'COMPLETE.json').read_text(encoding='utf-8'))
 require(done['manifestSha256']==sha(d/'manifest.json'),'MANIFEST_CHANGED')
 require(m['archive']=='zj-market-b06-public.zip','UNEXPECTED_ARCHIVE_NAME')
 require(m['archiveSha256']==sha(d/m['archive']),'ARCHIVE_CHANGED')
 with zipfile.ZipFile(d/m['archive']) as z:
  names=z.namelist();require(len(names)==len(set(names)),'DUPLICATE_ZIP_PATH')
  require(set(names)==set(m['files'])|{'DELIVERY-MANIFEST.json'},'UNEXPECTED_ZIP_SET')
  for name,h in m['files'].items():
   require(safe(name),'UNSAFE_ZIP_PATH');require(hashlib.sha256(z.read(name)).hexdigest()==h,'ZIP_MEMBER_CHANGED')
  inner=json.loads(z.read('DELIVERY-MANIFEST.json'));require(inner=={k:v for k,v in m.items() if k not in ['archive','archiveSha256','archiveBytes']},'INNER_MANIFEST_CHANGED')
 return m
def build(name):
 import re
 require(bool(re.fullmatch(r'b067-[a-z0-9-]{1,40}',name)),'INVALID_BATCH')
 work=HOME/name;require(not work.exists(),'FRESH_DELIVERY_REQUIRED')
 # Enumerate actual tracked AND nonignored new files; git archive HEAD would omit this work.
 paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
 require(all(safe(p) for p in paths),'UNSAFE_SOURCE_CANDIDATE')
 require(all((ROOT/p).is_file() and not (ROOT/p).is_symlink() for p in paths),'NONREGULAR_SOURCE_CANDIDATE')
 final=json.loads((ROOT/'docs/tests/b06-final-acceptance.json').read_text(encoding='utf-8'));require(final['stageCompletion'] and final['status']=='PASSED_WINDOWS_FINAL_PINNED_CANDIDATE','FINAL_NOT_PASSED')
 for p,h in final['finalAcceptanceSourceSha256'].items():require(sha(ROOT/p)==h,'FINAL_SOURCE_DRIFT')
 # Scan exact private values without printing them. Generic example credentials are not runtime secrets.
 values=list(json.loads((ROOT/'.local/b06/runtime/private/values.json').read_text()).values())
 values += [v['password'] for v in json.loads((ROOT/'.local/b06/control/demo-accounts.json').read_text()).values()]
 for p in paths:
  data=(ROOT/p).read_bytes()
  require(not any(str(v).encode() in data for v in values),'PRIVATE_VALUE_IN_PUBLIC_SOURCE:'+p)
  require(not re.search(rb'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----\r?\n[A-Za-z0-9+/=\r\n]{32,}-----END',data),'PRIVATE_KEY_IN_PUBLIC_SOURCE:'+p)
 work.mkdir(parents=True)
 source={p:sha(ROOT/p) for p in sorted(paths)}
 inner={'format':1,'stage':'B-06.7','runName':name,'generatedAt':datetime.now(timezone.utc).isoformat(),'baseHead':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),'uncommittedWorktree':True,'gitPublished':False,'scope':'Public source, templates, sanitized evidence and manuals; no images, private A input, runtime data or keys','files':source}
 archive=work/'zj-market-b06-public.zip'
 with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
  for p in source:z.write(ROOT/p,p)
  z.writestr('DELIVERY-MANIFEST.json',json.dumps(inner,ensure_ascii=False,indent=2)+'\n')
 m=dict(inner,archive=archive.name,archiveSha256=sha(archive),archiveBytes=archive.stat().st_size)
 (work/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (work/'COMPLETE.json').write_text(json.dumps({'manifestSha256':sha(work/'manifest.json')})+'\n',encoding='utf-8');verify(work)
 print('PUBLIC_DELIVERY_PASS '+json.dumps({'runName':name,'files':len(source),'bytes':m['archiveBytes'],'sha256':m['archiveSha256']}))
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','verify']);p.add_argument('--run-name');p.add_argument('--directory');a=p.parse_args()
 if a.action=='build':require(a.run_name is not None,'RUN_NAME_REQUIRED');build(a.run_name)
 else:require(a.directory is not None,'DIRECTORY_REQUIRED');m=verify(a.directory);print('DELIVERY_VERIFY_PASS '+str(len(m['files'])))
if __name__=='__main__':main()
