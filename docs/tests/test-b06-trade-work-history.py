"""Execute the observer history predicate against isolated relational fixtures.
SQLite supplies JSON/SHA helpers; actual MySQL/TLS query is verified separately.
"""
from pathlib import Path
import hashlib,importlib.util,json,sqlite3,unittest
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('observer',ROOT/'scripts/b06-observability.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class HistoryTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(':memory:');self.db.execute("ATTACH ':memory:' AS zj_market_b06")
  self.db.create_function('SHA2',2,lambda v,n:hashlib.sha256(v.encode() if isinstance(v,str) else v).hexdigest() if v is not None else None)
  self.db.create_function('JSON_UNQUOTE',1,lambda x:x)
  def extract(raw,path):
   if raw is None:return None
   v=json.loads(raw)
   for key in path[2:].split('.'):
    if not isinstance(v,dict):return None
    v=v.get(key)
   return v
  self.db.create_function('JSON_EXTRACT',2,extract)
  tables={
   'b_trade_work':'work_id TEXT,order_id TEXT,team_id TEXT,state TEXT,kind TEXT,lease_token TEXT,lease_until_ms INT,evidence TEXT,evidence_hash TEXT',
   'b_market_order':'order_id TEXT,business_status TEXT,a_evidence TEXT',
   'b_payment':'order_id TEXT,payment_id TEXT,amount INT,funds_state TEXT,a_acceptance TEXT',
   'b_refund':'order_id TEXT,payment_id TEXT,amount INT,funds_status TEXT,sync_status TEXT,release_status TEXT',
   'b_inventory_reservation':'order_id TEXT,state TEXT',
   'b_reconciliation_task':'team_id TEXT,source TEXT,channel TEXT,state TEXT',
   'b_inventory_ledger':'order_id TEXT,kind TEXT',
   'b_fulfillment':'order_id TEXT',
   'b_order_block':'order_id TEXT,state TEXT,kind TEXT'}
  for t,columns in tables.items():self.db.execute('CREATE TABLE zj_market_b06.'+t+'('+columns+')')
  self.evidence=json.dumps({'source':'b06','channel':'web','payload':{'teamId':'team'}})
  rows={
   'b_trade_work':('work','order','team','DEFERRED_B05','TEAM_FAILED',None,None,self.evidence,hashlib.sha256(self.evidence.encode()).hexdigest()),
   'b_market_order':('order','CLOSED',json.dumps({'source':'b06','channel':'web','teamId':'team'})),
   'b_payment':('order','payment',90,'SUCCEEDED','ACCEPTED'),
   'b_refund':('order','payment',90,'SUCCEEDED','ACCEPTED','RELEASED'),
   'b_inventory_reservation':('order','RELEASED'),
   'b_reconciliation_task':('team','b06','web','RESOLVED'),
   'b_inventory_ledger':('order','RELEASE')}
  for t,row in rows.items():self.db.execute('INSERT INTO zj_market_b06.'+t+' VALUES('+','.join('?' for _ in row)+')',row)
  # BLOB charset conversion is MySQL-specific; no predicate or join is changed.
  self.predicate=m.historical_team_handoff_sql().replace('CONVERT(q.evidence USING utf8mb4)','q.evidence')
 def tearDown(self):self.db.close()
 def historical(self):return self.db.execute('SELECT COALESCE(('+self.predicate+'),FALSE) FROM zj_market_b06.b_trade_work q WHERE work_id=?',('work',)).fetchone()[0]
 def test_terminal_bound_team_handoff_is_history_and_original_row_is_retained(self):
  for kind in ['TEAM_FAILED','TEAM_RECONCILIATION_REQUIRED']:
   self.db.execute('UPDATE zj_market_b06.b_trade_work SET kind=?',(kind,));self.assertEqual(1,self.historical())
  self.assertEqual('DEFERRED_B05',self.db.execute('SELECT state FROM zj_market_b06.b_trade_work').fetchone()[0])
 def test_any_missing_or_conflicting_terminal_fact_remains_active(self):
  mutations=[
   ("UPDATE b_trade_work SET state='LEASED'",),
   ("UPDATE b_trade_work SET kind='REFUND_OBLIGATION'",),
   ("UPDATE b_trade_work SET lease_token='active'",),
   ("UPDATE b_trade_work SET lease_until_ms=1",),
   ("UPDATE b_trade_work SET evidence_hash='mismatch'",),
   ("UPDATE b_trade_work SET evidence=NULL",),
   ("UPDATE b_trade_work SET team_id='other'",),
   ("UPDATE b_trade_work SET order_id='other'",),
   ("UPDATE b_market_order SET business_status='WAITING_REFUND'",),
   ("UPDATE b_market_order SET a_evidence=NULL",),
   ("UPDATE b_payment SET funds_state='UNKNOWN'",),
   ("UPDATE b_payment SET a_acceptance='PENDING'",),
   ("UPDATE b_refund SET amount=89",),
   ("UPDATE b_refund SET payment_id='other'",),
   ("UPDATE b_refund SET funds_status='UNKNOWN'",),
   ("UPDATE b_refund SET sync_status='PENDING'",),
   ("UPDATE b_refund SET release_status='HELD'",),
   ("UPDATE b_inventory_reservation SET state='HELD'",),
   ("UPDATE b_reconciliation_task SET state='REVIEW_REQUIRED'",),
   ("UPDATE b_reconciliation_task SET source='other'",),
   ("UPDATE b_reconciliation_task SET channel='other'",),
   ("DELETE FROM b_inventory_ledger",),
   ("INSERT INTO b_inventory_ledger VALUES('order','RELEASE')",),
   ("INSERT INTO b_inventory_ledger VALUES('order','CONFIRM')",),
   ("INSERT INTO b_fulfillment VALUES('order')",),
   ("INSERT INTO b_order_block VALUES('order','ACTIVE','PAYMENT')",),
   ("INSERT INTO b_trade_work(work_id,order_id,state) VALUES('conflict','order','REVIEW_REQUIRED')",)]
  for (sql,) in mutations:
   with self.subTest(sql=sql):
    self.db.execute('SAVEPOINT negative');self.db.execute(sql);self.assertEqual(0,self.historical());self.db.execute('ROLLBACK TO negative');self.db.execute('RELEASE negative')
 def test_original_evidence_source_channel_and_team_must_match(self):
  for key,value in [('source','other'),('channel','other'),('payload',{'teamId':'other'})]:
   with self.subTest(key=key):
    e=json.loads(self.evidence);e[key]=value;e=json.dumps(e);self.db.execute('UPDATE zj_market_b06.b_trade_work SET evidence=?,evidence_hash=?',(e,hashlib.sha256(e.encode()).hexdigest()));self.assertEqual(0,self.historical())
if __name__=='__main__':unittest.main()
