"""Bind final immutable candidate and per-stage evidence; no historical success rewriting."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,importlib.util
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
def main():
 evidence={
 'B-06.0':'docs/tests/b06-baseline-closeout-20261011.json',
 'B-06.1':'docs/tests/b06-images-acceptance.json',
 'B-06.2':'docs/tests/b06-startup-acceptance.json',
 'B-06.3':'docs/tests/b06-normal-acceptance.json',
 'B-06.4':'docs/tests/b06-observability-acceptance.json',
 'B-06.5':'docs/tests/b06-fault-acceptance.json',
 'B-06.6':'docs/tests/b06-backup-acceptance.json',
 'B-06.7':'docs/tests/b06-final-acceptance.json'}
 reports={k:read(v) for k,v in evidence.items()}
 require(all(r['status'].startswith('PASSED') for r in reports.values()),'INCOMPLETE_STAGE')
 final=reports['B-06.7'];require(final['stageCompletion'] and final['originalRestored'] and final['activeAlerts']==0,'FINAL_ORIGINAL_NOT_RECOVERED')
 for path,h in final['finalAcceptanceSourceSha256'].items():require(sha(ROOT/path)==h,'FINAL_SOURCE_DRIFT')
 faults=read('docs/b06-fault-release.json');back=read('docs/b06-backup-release.json')
 require(faults['images']==back['ordinaryImages'],'CANDIDATE_MISMATCH')
 for service,key in [('marketing-a','a'),('market-b','b'),('web','web')]:require(final['images'][service]==faults['images'][key],'FINAL_BROWSER_IMAGE_MISMATCH')
 for rel in [faults,back]:
  for field in ['sourceSha256','artifactSha256']:
   for path,h in rel[field].items():require(sha(ROOT/path).lower()==h.lower(),'RELEASE_SOURCE_OR_ARTIFACT_DRIFT:'+path)
 base=ROOT/'.local/b06'
 for part,empty in [('backups',{}),('faults',[])]:
  for f in (base/part).glob('*/recovery.json'):require(json.loads(f.read_text())==empty,'PENDING_RECOVERY')
 work=base/'backups'/final['recoveryRun'];require(sha(work/'progress.json')==final['rawRecoveryReportSha256'],'RAW_FINAL_RECOVERY_CHANGED')
 require(json.loads((work/'progress.json').read_text())['status']=='PASSED','FINAL_RAW_FAILED')
 packaging=read('.local/b06/packaging/b067-final-packaging-20261012-01/report.json');maintenance=read('.local/b06/maintenance-integrity/b067-final-maintenance-20261012-01/report.json')
 require(packaging['status']==maintenance['status']=='PASSED' and len(packaging['checks'])==33 and len(maintenance['checks'])==9,'PACKAGING_NOT_VERIFIED')
 containers=json.loads(subprocess.check_output(['docker','--context','desktop-linux','inspect']+['zj-market-b06-'+s+'-1' for s in ['mysql','redis','namesrv','broker','marketing-a','market-b','web']],text=True))
 require(all(c['State']['Health']['Status']=='healthy' and not c['State']['OOMKilled'] for c in containers),'ORIGINAL_CONTAINERS_NOT_HEALTHY')
 for s,k in [('marketing-a','a'),('market-b','b'),('web','web')]:require(next(c for c in containers if c['Config']['Labels']['com.docker.compose.service']==s)['Image']==faults['images'][k],'ORIGINAL_IMAGE_DRIFT')
 tests=subprocess.run(['python','-B',ROOT/'docs/tests/test-b06-delivery.py'],capture_output=True,text=True,encoding='utf-8');require(tests.returncode==0 and 'Ran 6 tests' in tests.stderr,'DELIVERY_GUARDS_FAILED')
 (base/'delivery-guard-tests.log').write_text(tests.stdout+tests.stderr,encoding='utf-8')
 source_paths=sorted(set(final['finalAcceptanceSourceSha256'])|{'docs/tests/test-b06-delivery.py','scripts/b06-delivery.py','docs/tests/collect-b06-delivery.py','deploy/b06/DELIVERY.md','deploy/b06/compose.yml'})
 release={'format':1,'stage':'B-06.7','status':'LOCAL_TESTED_WINDOWS_FINAL_DELIVERY','stageCompletion':True,'generatedAt':datetime.now(timezone.utc).isoformat(),'images':faults['images'],'allRuntimeImages':final['images'],'maintenanceImage':back['maintenanceImage'],'sdkImage':back['sdkImage'],'schemaProtocol':'B V1-V18 (19 migrations); opaque rosterVersion preserved','compatibility':'Same tested business jar packaging rollback only; unknown older business binaries rejected','baselineHead':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'branch':'b-06','uncommittedWorktree':True,'gitPublished':False,'registryPublished':False,'linuxVmValidated':False,'finalBrowserChecks':len(final['browserChecks']),'finalAccountingChecks':len(final['accountingChecks']),'finalRecoveryChecks':len(final['recoveryChecks']),'deliveryGuardTests':6,'deliveryGuardLogSha256':sha(base/'delivery-guard-tests.log'),'finalPackagingChecks':33,'finalMaintenanceChecks':9,'applicationTests':{'count':111,'execution':'Historical B065 JUnit; existing result and actual image bytes rechecked, not rerun in B067'},'evidence':{k:{'path':p,'sha256':sha(ROOT/p),'status':reports[k]['status'],'historical':k!='B-06.7'} for k,p in evidence.items()},'sourceSha256':{p:sha(ROOT/p) for p in source_paths},'historicalProvenance':'Each stage retains exact run/source/image hashes. B063 ran earlier B image; B067 reruns complete real browser on final B065 image. Shared browser/collector isolation arguments added only for B067; old reports are unchanged. B067 freshly restores sealed backup, repeats message/release recovery and full browser; full destructive B065 matrix is referenced, not rerun.','originalFinancialSha256':final['originalFinancialSha256'],'originalChannelSha256':final['originalChannelSha256'],'finalRawRecoverySha256':final['rawRecoveryReportSha256'],'privateInputs':['Sealed B066 backup, full secrets and immutable images; never public','Pinned A original binary/contract/doc for fresh source builds; exact source build commit unproven'],'limits':['Windows Docker Linux/amd64 only; Linux VM/LAN other clients not validated','No genuine third-party money, shipment/receipt, partial refund or generic REVIEW clearing','Local unencrypted protected backup; no offhost, PITR, online backup, power loss or disk loss','No arbitrary older business binary rollback or schema downgrade','Watch manual; local alerts only; MQ consumer lag not collected','Windows-specific paths/context/resource/ACL checks require explicit Linux port and retest','All original failed batches, audits, quarantines and closed historical reviews retained']}
 text=json.dumps(release,ensure_ascii=False,indent=2)+'\n';(ROOT/'docs/b06-final-release.json').write_text(text,encoding='utf-8')
 index={'format':1,'stage':'B-06.7','status':'FINAL_PUBLIC_DELIVERY_INDEX','releasePath':'docs/b06-final-release.json','releaseSha256':sha(ROOT/'docs/b06-final-release.json'),'manual':'deploy/b06/DELIVERY.md','publicPackage':'.local/b06/delivery/b067-20261012-01/zj-market-b06-public.zip','packageVerification':'Sibling manifest.json and COMPLETE.json bind ZIP SHA256 and all file hashes; no self-referential hash in this index','privateBackup':'.local/b06/backups/b066-20261012-02','privateBackupManifestSha256':reports['B-06.6']['backup']['manifestSha256'],'privateOriginalAInputManifest':'docs/b06-a-release-manifest.json','allRuntimeImages':final['images'],'gitPublished':False,'linuxVmValidated':False}
 (ROOT/'docs/b06-delivery-manifest.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('B067_DELIVERY_EVIDENCE_PASS '+json.dumps({'browser':len(final['browserChecks']),'accounting':len(final['accountingChecks']),'recovery':len(final['recoveryChecks'])}))
if __name__=='__main__':main()
