"""Build pinned Linux images from allowlisted contexts, recording image IDs and input hashes.
Run B Maven package and frontend npm ci/build first. No publish or full-stack startup.
"""
from pathlib import Path
import argparse,json,subprocess,hashlib
import importlib.util
spec=importlib.util.spec_from_file_location("prepare_b06_images",Path(__file__).with_name("prepare-b06-images.py"))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);prepare=module.prepare
ROOT=Path(__file__).resolve().parents[1]
def main(java_home,context):
 prepare(java_home)
 lock=json.loads((ROOT/'deploy/b06/images.lock.json').read_text());out=ROOT/'.local/b06/build'
 inputs=json.loads((out/'artifact-manifest.json').read_text());images={}
 for service,key in [('a','java8'),('b','java21'),('web','web')]:
  fingerprint=hashlib.sha256(json.dumps(inputs['contexts'][service],sort_keys=True).encode()).hexdigest()[:16]
  tag='zj-market-b06/'+service+':'+fingerprint
  subprocess.run(['docker','--context',context,'build','--platform','linux/amd64','--build-arg','BASE_IMAGE='+lock[key],'-t',tag,str(out/service)],check=True)
  data=json.loads(subprocess.check_output(['docker','--context',context,'image','inspect',tag]))[0]
  images[service]={'tag':tag,'id':data['Id'],'base':lock[key],'architecture':data['Architecture'],'os':data['Os']}
 manifest={'schemaVersion':1,'inputs':inputs,'images':images,'baseImages':lock,'publication':'LOCAL_ONLY; no registry push; image ID is local content digest'}
 (out/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (out/'release.env').write_text('B06_SECRET_DIR='+str(ROOT/'.local/b06/runtime').replace('\\','/')+'\n'+''.join('B06_'+s.upper()+'_IMAGE='+v['id']+'\n' for s,v in images.items()))
 print('Local image build complete; immutable IDs in release.env, no stack started.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--java-home',required=True);p.add_argument('--context',default='desktop-linux');a=p.parse_args();main(a.java_home,a.context)
