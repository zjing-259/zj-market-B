"""Backup integrity/ownership/compatibility guards. Uses isolated archives, never real volumes."""
from pathlib import Path
import importlib.util,tempfile,json,tarfile,io,unittest,hashlib
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[2];s=importlib.util.spec_from_file_location('backup',ROOT/'scripts/b06-backup.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class BackupGuards(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.work=Path(self.temp.name)
  self.files=['images.tar','business-before.sql','original-event.json','compose-snapshot.json','state-before.json','recovery-tools.json','bundle/control/state.json','bundle/control/demo-accounts.json','bundle/runtime/private/values.json','bundle/images.lock.json','bundle/init/b_runtime-tables.txt']
  for name in self.files:
   p=self.work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'isolated fixture')
  with tarfile.open(self.work/'images.tar','w') as f:
   for name,data in [('manifest.json',b'[{"Config":"config.json","Layers":[]}]'),('config.json',b'{}')]:
    t=tarfile.TarInfo(name);t.size=len(data);f.addfile(t,io.BytesIO(data))
  for name in m.VOLUMES:
   with tarfile.open(self.work/(name+'.tar'),'w') as f:
    t=tarfile.TarInfo('./data');t.size=3;f.addfile(t,io.BytesIO(b'old'))
   self.files.append(name+'.tar')
  m.atomic(self.work/'state-before.json',{'inputs':{'deploy/b06/init/b_runtime-tables.txt':m.sha(self.work/'bundle/init/b_runtime-tables.txt')}});self.refresh()
 def tearDown(self):self.temp.cleanup()
 def refresh(self):
  m.atomic(self.work/'manifest.json',{'format':2,'images':['sha256:'+hashlib.sha256(b'{}').hexdigest()],'project':m.PROJECT,'volumes':list(m.VOLUMES),'files':{name:m.sha(self.work/name) for name in self.files}});m.atomic(self.work/'COMPLETE.json',{'manifestSha256':m.sha(self.work/'manifest.json')})
 def test_complete_intact_set_is_accepted(self):self.assertEqual(m.PROJECT,m.validate_manifest(self.work)['project'])
 def test_corrupt_archive_is_rejected(self):
  (self.work/'mysql-data.tar').write_bytes(b'corrupt')
  with self.assertRaisesRegex(RuntimeError,'BACKUP_HASH_MISMATCH'):m.validate_manifest(self.work)
 def test_missing_completion_is_rejected(self):
  (self.work/'COMPLETE.json').unlink()
  with self.assertRaisesRegex(RuntimeError,'INCOMPLETE_BACKUP'):m.validate_manifest(self.work)
 def test_manifest_tamper_is_rejected(self):
  (self.work/'manifest.json').write_text('{}')
  with self.assertRaisesRegex(RuntimeError,'MANIFEST_HASH_MISMATCH'):m.validate_manifest(self.work)
 def test_missing_secret_component_even_with_valid_hashes_is_rejected(self):
  self.files.remove('bundle/runtime/private/values.json');self.refresh()
  with self.assertRaisesRegex(RuntimeError,'MISSING_BACKUP_COMPONENT'):m.validate_manifest(self.work)
 def test_escaping_manifest_path_is_rejected(self):
  p=self.work/'manifest.json';d=json.loads(p.read_text());d['files']['../outside']='anything';m.atomic(p,d);m.atomic(self.work/'COMPLETE.json',{'manifestSha256':m.sha(p)})
  with self.assertRaisesRegex(RuntimeError,'UNSAFE_OR_MISSING_ARCHIVE'):m.validate_manifest(self.work)
 def test_tar_traversal_or_external_symlink_rejected(self):
  for name,link in [('../escape',None),('safe','/outside')]:
   with self.subTest(name=name):
    with tarfile.open(self.work/'mysql-data.tar','w') as f:
     t=tarfile.TarInfo(name)
     if link:t.type=tarfile.SYMTYPE;t.linkname=link
     f.addfile(t)
    self.refresh()
    with self.assertRaisesRegex(RuntimeError,'UNSAFE_ARCHIVE'):m.validate_manifest(self.work)
 def test_wrong_project_or_incomplete_volume_set_is_rejected(self):
  for field,value in [('project','shared'),('volumes',['mysql-data'])]:
   self.refresh();p=self.work/'manifest.json';d=json.loads(p.read_text());d[field]=value;m.atomic(p,d);m.atomic(self.work/'COMPLETE.json',{'manifestSha256':m.sha(p)})
   with self.assertRaisesRegex(RuntimeError,'BACKUP_SCOPE_MISMATCH'):m.validate_manifest(self.work)
 def test_batch_names_cannot_escape_or_target_another_project(self):
  for name in ['../b066-test','b-06','b066-','b066-'+('x'*41),'b066-test;rm']:
   with self.assertRaises(RuntimeError):m.valid_name(name)
  m.valid_name('b066-test-01')
 def test_incompatible_protocol_schema_history_jar_and_same_id_rejected(self):
  state={'schemaFingerprint':'schema','migrationHistoryHash':'history'};valid={'protocol':'V18-opaque-rosterVersion',**state,'businessJarSha256':'jar','candidate':{'id':'new'},'rollbackImage':'old'};m.compatible(valid,state,'jar')
  for key,value in [('protocol','old'),('schemaFingerprint','other'),('migrationHistoryHash','other'),('businessJarSha256','other'),('rollbackImage','new')]:
   with self.assertRaises(RuntimeError):m.compatible(dict(valid,**{key:value}),state,'jar')
 def test_image_archive_must_contain_every_claimed_config_not_just_local_cache(self):
  p=self.work/'manifest.json';d=json.loads(p.read_text());d['images'].append('sha256:missing');m.atomic(p,d);m.atomic(self.work/'COMPLETE.json',{'manifestSha256':m.sha(p)})
  with self.assertRaisesRegex(RuntimeError,'ARCHIVED_IMAGE_SET_INCOMPLETE'):m.validate_manifest(self.work)
 def test_initialization_inputs_cannot_be_substituted_with_rehashed_bundle(self):
  (self.work/'bundle/init/b_runtime-tables.txt').write_bytes(b'different');self.refresh()
  with self.assertRaisesRegex(RuntimeError,'INITIALIZATION_INPUT_MISMATCH'):m.validate_manifest(self.work)
 def test_resolved_compose_network_names_are_replaced_with_isolated_names(self):
  config={'networks':{k:{'name':m.PROJECT+'_'+k} for k in ['edge','rpc','data','redis','mq']}};m.isolated_networks(config,'isolated')
  self.assertEqual({'isolated_'+k for k in config['networks']},{v['name'] for v in config['networks'].values()})
 def test_external_or_incomplete_network_set_is_rejected(self):
  for config in [{'networks':{'edge':{}}},{'networks':{k:{'external':True} for k in ['edge','rpc','data','redis','mq']}}]:
   with self.assertRaises(RuntimeError):m.isolated_networks(config,'isolated')
 def test_recover_before_snapshot_uses_durable_source_fingerprint(self):
  r=object.__new__(m.Recovery);r.clone='zj-market-b066-test';r.report={'originalFinancialBefore':'stable'};r.journal={'restoreOriginal':True,'original':{'mysql':{'id':'id','image':'image','volumes':{},'restart':{'Name':'unless-stopped','MaximumRetryCount':0}}}}
  r.docker_run=Mock(return_value=Mock(stdout=''));r.inspect=Mock(return_value={'Id':'id','Image':'image','Mounts':[]});r.d=Mock();r.d.state.return_value={'mode':'open','phase':'READY'};r.financial=Mock(return_value='stable');r.check=Mock();r.save=Mock();r.event=Mock();r.recover();r.financial.assert_called_once_with(m.PROJECT);self.assertEqual({},r.journal);self.assertTrue(r.report['originalRecovered'])
 def test_unowned_or_writable_original_volume_rejected_before_docker(self):
  r=object.__new__(m.Recovery);r.clone='zj-market-b066-test';r.docker_run=Mock()
  for volume,readonly in [('shared_mysql',True),(m.PROJECT+'_mysql-data',False)]:
   with self.assertRaises(RuntimeError):r.helper('test',volume,'true',readonly=readonly)
  r.docker_run.assert_not_called()
if __name__=='__main__':unittest.main()
