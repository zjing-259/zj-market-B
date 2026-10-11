"""Read-only A fixture quota audit. Container administrator stays separate from B runtime."""
import argparse,json,hashlib,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--joint-batch',required=True);p.add_argument('--run-name',required=True);a=p.parse_args()
 assert re.fullmatch('b056-[A-Za-z0-9-]+',a.joint_batch) and re.fullmatch('b056-[A-Za-z0-9-]+',a.run_name)
 out=R/'target/b05-joint'/a.run_name;out.mkdir(parents=True,exist_ok=False);result={'status':'RUNNING','scope':'read-only A isolated fixture schema via container administrator, not B runtime; exact current-batch teams only','teams':[]}
 try:
  joint=json.loads((R/'target/b05-joint'/a.joint_batch/'report.json').read_bytes());assert joint['status']=='PASSED';prefix=joint['prefix'];result['verificationJarSha256']=joint['verificationJarSha256'];queries=['SET SESSION TRANSACTION READ ONLY;','START TRANSACTION WITH CONSISTENT SNAPSHOT;'];cases=[]
  for case,mode,reserved,paid,status in [('none','reconciliation-recover',0,0,'FAILED'),('partial','refund-sync-recover',1,1,'FAILED'),('completed','reconciliation-completed',3,3,'COMPLETED')]:
   f=R/'target/b03-readiness'/(prefix+'-'+case)/(mode+'-conservation.json');c=json.loads(f.read_bytes());assert c['status']=='PASSED' and len(c['orders'])==3;ids=[o['order_id'] for o in c['orders']];assert all(re.fullmatch('[A-Za-z0-9_-]{1,64}',i) for i in ids);cases.append((case,ids,reserved,paid,status));quoted=','.join("'"+i+"'" for i in ids)
   queries.append("SELECT JSON_OBJECT('case','"+case+"','teamId',t.team_id,'target',t.target_count,'reserved',t.reserved_count,'paid',t.paid_count,'status',t.team_status,'members',(SELECT COUNT(*) FROM ab_trade_order o WHERE o.team_id=t.team_id AND o.record_kind='RESERVATION'),'active',(SELECT COUNT(*) FROM ab_trade_order o WHERE o.team_id=t.team_id AND o.record_kind='RESERVATION' AND o.order_status<>'CANCELLED'),'paidOrders',(SELECT COUNT(*) FROM ab_trade_order o WHERE o.team_id=t.team_id AND o.order_status='PAID'),'ownMembers',(SELECT COUNT(*) FROM ab_trade_order o WHERE o.team_id=t.team_id AND o.out_trade_no IN ("+quoted+"))) FROM ab_team t WHERE t.source='s01' AND t.channel='c01' AND t.team_id=(SELECT team_id FROM ab_trade_order WHERE source='s01' AND channel='c01' AND out_trade_no='"+ids[0]+"');")
  queries.append('COMMIT;');run=subprocess.run(['docker','exec','-i','mysql','sh','-c','export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mysql -uroot group_buy_market_phase1_test --batch --skip-column-names'],input='\n'.join(queries)+'\n',text=True,capture_output=True);assert run.returncode==0,'Read-only isolated A query failed (credentials withheld)';rows=[json.loads(x) for x in run.stdout.splitlines() if x.strip()];assert len(rows)==3
  for case,ids,reserved,paid,status in cases:
   row=next(x for x in rows if x['case']==case);assert row['target']==3 and row['members']==3 and row['ownMembers']==3 and row['reserved']==row['active']==reserved and row['paid']==row['paidOrders']==paid and row['status']==status,case+' quota mismatch';result['teams'].append(row)
  result['status']='PASSED'
 except Exception as e:result['status']='FAILED';result['errorType']=type(e).__name__;result['error']=str(e)
 (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('B056 exact actual A quota audit: '+result['status']);return 0 if result['status']=='PASSED' else 1
if __name__=='__main__':raise SystemExit(main())
