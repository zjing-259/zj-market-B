"""Recovery safety contracts, with no Docker or business writes."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('faults',ROOT/'scripts/b06-faults.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Guards(unittest.TestCase):
 def bare(self):
  f=m.Faults.__new__(m.Faults);f.inspect=Mock();f.docker=Mock();f.healthy=Mock();f.save=Mock();f.event=Mock();f.actions=[];return f
 def test_rejects_wrong_project_before_any_mutation(self):
  f=self.bare();del f.inspect;f.docker.return_value.stdout=json.dumps([{'Config':{'Labels':{'com.docker.compose.project':'shared','com.docker.compose.service':'mysql'}}}])
  with self.assertRaisesRegex(RuntimeError,'OWNERSHIP_MISMATCH'):f.inspect('mysql')
  self.assertEqual(f.docker.call_count,1)
 def test_rejects_unlisted_service(self):
  f=self.bare();del f.inspect
  with self.assertRaisesRegex(RuntimeError,'SERVICE_NOT_ALLOWLISTED'):f.inspect('shared-mysql')
  f.docker.assert_not_called()
 def test_unlisted_network_inverse_cannot_touch_any_endpoint(self):
  f=self.bare()
  with self.assertRaisesRegex(RuntimeError,'NETWORK_NOT_ALLOWLISTED'):f.restore({'kind':'network','service':'market-b','network':'shared_rpc'})
  f.inspect.assert_not_called();f.docker.assert_not_called()
 def test_runtime_image_drift_refuses_force_recreate(self):
  f=self.bare();f.inspect.return_value={'image':'changed'};f.run=Mock()
  with self.assertRaisesRegex(RuntimeError,'RUNTIME_IMAGE_DRIFT'):f.restore({'kind':'runtime','service':'market-b','baseline':{'image':'original'}})
  f.run.assert_not_called();f.docker.assert_not_called()
 def test_absent_refund_rows_stay_unknown_during_natural_expiry_wait(self):
  f=self.bare();f.query=Mock(return_value='NULL');self.assertIsNone(f.jsonquery('SELECT JSON_ARRAYAGG(...)'))
 def test_stale_container_inverse_cannot_touch_replacement(self):
  f=self.bare();f.inspect.return_value={'id':'replacement'}
  with self.assertRaisesRegex(RuntimeError,'CONTAINER_REPLACED'):f.restore({'kind':'container','service':'mysql','id':'old'})
  f.docker.assert_not_called()
 def test_inverse_is_persisted_before_interrupt(self):
  f=self.bare();order=[];f.inspect.return_value={'id':'owned','restart':{'Name':'unless-stopped','MaximumRetryCount':0},'state':{'Running':True}};f.save.side_effect=lambda:order.append('save');f.docker.side_effect=lambda *a,**k:order.append('mutation');f.restore=Mock()
  # Stop deliberately fails the stopped-state assertion; the saved inverse still precedes mutation and finally runs.
  with self.assertRaises(RuntimeError):
   with f.down('mysql'):pass
  self.assertEqual(order[0],'save');f.restore.assert_called_once();self.assertEqual(len(f.actions),1)
 def test_failed_restore_retains_inverse(self):
  f=self.bare();f.inspect.return_value={'id':'owned'};f.docker.side_effect=RuntimeError('restore failed');a={'kind':'container','service':'mysql','id':'owned','restart':{'Name':'unless-stopped','MaximumRetryCount':0}};f.actions=[a]
  with self.assertRaises(RuntimeError):f.restore(a)
  self.assertEqual(f.actions,[a]);f.healthy.assert_not_called()
 def test_recover_continues_other_independent_inverses(self):
  f=self.bare();f.actions=[{'service':'a'},{'service':'b'}];f.report={};seen=[]
  def restore(a):
   seen.append(a['service'])
   if a['service']=='b':raise RuntimeError('failed')
  f.restore=restore
  with self.assertRaisesRegex(RuntimeError,'RECOVERY_INCOMPLETE'):f.recover()
  self.assertEqual(seen,['b','a']);self.assertEqual(f.report['recoveryErrors'],['failed'])
if __name__=='__main__':unittest.main()
