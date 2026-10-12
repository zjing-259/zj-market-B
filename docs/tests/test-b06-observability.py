"""Isolated observer behavior; no business fixtures or Docker changes."""
from pathlib import Path
import importlib.util,json,tempfile,unittest,time,sys,contextlib,io
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('observation',ROOT/'scripts/b06-observability.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ObservationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=m.HOME;m.HOME=Path(self.temp.name);self.o=m.Observer()
 def tearDown(self):m.HOME=self.old;self.temp.cleanup()
 def sample(self,db='OK',review=0,overdue=0):
  return {'at':m.stamp(),'health':{'web':{'ok':True}},'databaseStatus':db,'obligations':{'activeOrderReview':0,'activePaymentReview':0,'nonReconciliationBlocksActive':0,'paymentAwaitingA':0,'paymentAwaitingAOldestSeconds':0,'refundUnfinished':0,'refundUnfinishedOldestSeconds':0},'queues':{'test':{'due':int(overdue>0),'oldestOverdueSeconds':overdue,'review':review}}}
 def events(self):return [json.loads(v) for v in (m.HOME/'alerts.jsonl').read_text().splitlines()]
 def test_unknown_does_not_resolve_business_alert_and_repeat_is_deduplicated(self):
  self.o.alerts(self.sample(review=1));self.o.alerts(self.sample(review=1));self.assertEqual(1,len(self.events()))
  self.o.alerts(self.sample(db='UNKNOWN'));self.assertTrue(m.load('alerts-state.json')['review:test']['active'])
  self.o.alerts(self.sample());events=self.events();start=[v for v in events if v['key']=='review:test' and v['event']=='alert_firing'][0];end=[v for v in events if v['key']=='review:test' and v['event']=='alert_resolved'][0];self.assertEqual(start['incidentId'],end['incidentId'])
 def test_future_and_short_wait_do_not_alert_but_old_due_does(self):
  self.o.alerts(self.sample(overdue=299));self.assertFalse((m.HOME/'alerts.jsonl').exists())
  self.o.alerts(self.sample(overdue=300));self.assertEqual('backlog:test',self.events()[0]['key'])
 def test_rotation_is_bounded(self):
  for i in range(20):m.append('rotation.jsonl',{'i':i,'v':'x'*40},limit=60,backups=3)
  self.assertEqual(4,len(list(m.HOME.glob('rotation.jsonl*'))));self.assertFalse((m.HOME/'rotation.jsonl.4').exists())
 def test_crash_intent_replays_same_incident(self):
  event={'at':m.stamp(),'key':'review:test','event':'alert_firing','incidentId':'same-id'}
  m.atomic('alerts-pending.json',{'event':event,'state':{'review:test':{'active':True,'incidentId':'same-id'}}})
  self.o.alerts(self.sample(review=1));self.assertEqual('same-id',self.events()[0]['incidentId']);self.assertFalse((m.HOME/'alerts-pending.json').exists())
 def test_trace_rejects_sql_and_control_characters_before_query(self):
  for identity in ("x' OR 1=1",'x\nprivate','x'*65):
   with self.assertRaises(ValueError):self.o.trace('order',identity)
 def test_stale_or_unhealthy_status_fails_without_claiming_freshness(self):
  for age,complete in ((100,True),(0,False)):
   m.atomic('latest.json',{'sampleEpoch':time.time()-age,'complete':complete})
   with patch.object(sys,'argv',['observer','status']),contextlib.redirect_stdout(io.StringIO()) as out:
    self.assertEqual(2,m.main())
   self.assertFalse(json.loads(out.getvalue())['ok'])
 def test_one_collector_only(self):
  with m.exclusive():
   with self.assertRaises(OSError):
    with m.exclusive():pass
if __name__=='__main__':unittest.main()
