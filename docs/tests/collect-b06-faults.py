"""Publish a redacted B065 summary only after actual business/recovery/security evidence passes."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,subprocess,importlib.util,time
ROOT=Path(__file__).resolve().parents[2]
def require(v,message):
 if not v:raise RuntimeError(message)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-name',required=True);p.add_argument('--recovery-run',required=True);p.add_argument('--security-run',required=True);p.add_argument('--runtime-gap-run',required=True);a=p.parse_args()
 home=ROOT/'.local/b06/faults';work=home/a.run_name
 reports={kind:json.loads((home/name/'progress.json').read_text(encoding='utf-8')) for kind,name in [('business',a.run_name),('interruptedRecovery',a.recovery_run),('securityPreflight',a.security_run),('runtimeGap',a.runtime_gap_run)]}
 for kind,r in reports.items():
  require(r['status']=='PASSED',kind+' not passed');require(json.loads((home/r['runName']/'recovery.json').read_text())==[],kind+' has pending inverses')
 business=reports['business'];source=json.loads((work/'source-during-run.json').read_text())
 require(all(sha(ROOT/f)==v for f,v in source.items()),'Fault source drift since actual run')
 require(len(business['facts'])==4 and sum(len(v['orders']) for v in business['facts'].values())==7,'Incomplete actual business facts')
 tests=subprocess.run(['python','-B',ROOT/'docs/tests/test-b06-faults.py'],capture_output=True,text=True,encoding='utf-8');(work/'guard-tests.log').write_text(tests.stdout+tests.stderr,encoding='utf-8');require(tests.returncode==0 and 'Ran 9 tests' in tests.stderr,'Guard tests failed')
 spec=importlib.util.spec_from_file_location('obs',ROOT/'scripts/b06-observability.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 with m.exclusive():
  observation=m.Observer().sample();require(observation['complete'],'Final observation incomplete');alerts=json.loads((m.HOME/'alerts-state.json').read_text());require(not any(v['active'] for v in alerts.values()),'Active alerts remain')
  events=[]
  for path in sorted(m.HOME.glob('alerts.jsonl*')):
   for line in path.read_text(encoding='utf-8').splitlines():
    e=json.loads(line)
    if e['at']>=business['startedAt']:events.append(e)
 events.sort(key=lambda e:e['at']);triggered={e['incidentId'] for e in events if e.get('event')=='alert_firing'};resolved={e['incidentId'] for e in events if e.get('event')=='alert_resolved'}
 require(len(triggered)>=6 and triggered<=resolved,'Actual alerts must fire and resolve with the same incident IDs')
 pairs=[];pending={}
 for e in business['timeline']:
  if e['event']=='interrupted':pending[(e['service'],'network' if e['mode']=='rpc-network-disconnect' else 'container')]=e
  if e['event']=='restored' and (e['service'],e['kind']) in pending:
   before=pending.pop((e['service'],e['kind']));pairs.append({'service':e['service'],'mode':before['mode'],'interruptedAt':before['at'],'healthyObservedAt':e['at'],'unavailableThroughProbeAndRecoverySeconds':round((datetime.fromisoformat(e['at'])-datetime.fromisoformat(before['at'])).total_seconds(),3)})
 require(not pending and len(pairs)>=9,'Incomplete real interruption/restoration pairs')
 convergence=[]
 for service,check in [('marketing-a','closed-once-aClose'),('broker','first-A-accepted'),('namesrv','completed-once-second'),('mysql','database-pools-recovered'),('market-b','closed-once-networkClose'),('redis','closed-once-redisClose'),('marketing-a','refund-A-sync-after-recovery')]:
  target=next(c for c in business['checks'] if c['name']==check);prior=[e for e in business['timeline'] if e['event']=='restored' and e['service']==service and e['at']<=target['at']];require(bool(prior),'Missing restore before business convergence');last=prior[-1];convergence.append({'service':service,'check':check,'restoredHealthyAt':last['at'],'businessObservedAt':target['at'],'secondsAfterHealthy':round((datetime.fromisoformat(target['at'])-datetime.fromisoformat(last['at'])).total_seconds(),3)})
 deployment=m.module('proof_deployment',ROOT/'scripts/b06-deployment.py').Deployment('desktop-linux');fixture=json.loads((work/'fixture.json').read_text());channelAudit=[]
 for name,o in fixture['orders'].items():
  oid=o['orderId'];paid=not name.endswith('Close');refund=name.startswith('refund')
  sql=f"SELECT JSON_OBJECT('paidRoots',(SELECT COUNT(*) FROM zj_market_b06.b_sim_payment sp JOIN zj_market_b06.b_payment p ON p.payment_id=sp.payment_id WHERE p.order_id='{oid}' AND sp.gate='PAID' AND sp.amount=p.amount),'originalPaymentValid',(SELECT COUNT(*) FROM zj_market_b06.b_payment p JOIN zj_market_b06.b_payment_attempt a ON a.attempt_id=p.success_attempt_id JOIN zj_market_b06.b_sim_attempt sa ON sa.attempt_id=a.attempt_id WHERE p.order_id='{oid}' AND p.success_hash=SHA2(p.success_fact,256) AND sa.request_hash=a.request_hash AND sa.paid_at_ms=p.paid_at_ms),'channelRefunded',(SELECT COALESCE(SUM(sr.refunded_amount),0) FROM zj_market_b06.b_sim_refund sr JOIN zj_market_b06.b_refund r ON r.refund_id=sr.refund_id WHERE r.order_id='{oid}'),'refundRequestMatches',(SELECT COUNT(*) FROM zj_market_b06.b_refund r JOIN zj_market_b06.b_refund_attempt a ON a.refund_id=r.refund_id JOIN zj_market_b06.b_sim_refund_attempt sa ON sa.attempt_id=a.attempt_id WHERE r.order_id='{oid}' AND sa.refund_id=r.refund_id AND sa.request_hash=a.request_hash AND sa.state='SUCCEEDED'),'originalPaidSnapshotIntact',(SELECT COUNT(*) FROM zj_market_b06.b_refund r JOIN zj_market_b06.b_payment p ON p.payment_id=r.payment_id WHERE r.order_id='{oid}' AND JSON_UNQUOTE(JSON_EXTRACT(CONVERT(r.snapshot USING utf8mb4),'$.successHash'))=p.success_hash AND JSON_UNQUOTE(JSON_EXTRACT(CONVERT(r.snapshot USING utf8mb4),'$.successFact'))=CONVERT(p.success_fact USING utf8mb4)),'paidAt',(SELECT paid_at_ms FROM zj_market_b06.b_payment WHERE order_id='{oid}'))";
  proof=json.loads(deployment.admin('b065-final-channel-'+name,sql));require(proof['paidRoots']==proof['originalPaymentValid']==int(paid),'Original channel paid fact mismatch');require(float(proof['channelRefunded'])==(90 if refund else 0) and proof['refundRequestMatches']==proof['originalPaidSnapshotIntact']==int(refund),'Original refund/channel snapshot mismatch')
  if paid:require(proof['paidAt']==round(datetime.fromisoformat(o['payment']['paidAt']).timestamp()*1000),'Original HTTP paidAt changed')
  channelAudit.append({'orderId':oid,**proof})
 newproof={k:v for k,v in business.items() if k not in ('error','recoveryErrors')};newproof.update(status='PASSED_WINDOWS_DOCKER_FAULT_AND_RECOVERY',stageCompletion=True,generatedAt=datetime.now(timezone.utc).isoformat(),sourceSha256=source,guardTests=9,channelAndOriginalPaidFactAudit=channelAudit,interruptionDurations=pairs,businessConvergence=convergence,interruptedRecovery={'runName':a.recovery_run,'intentionalExitCode':reports['interruptedRecovery']['intentionalExitCode'],'checks':reports['interruptedRecovery']['checks']},runtimeGapRecovery={'runName':a.runtime_gap_run,'explicitControlledOpenFallback':reports['runtimeGap']['explicitControlledOpenFallback'],'checks':reports['runtimeGap']['checks']},securityPreflight={'runName':a.security_run,'checks':reports['securityPreflight']['checks']},rawReportSha256={k:sha(home/r['runName']/'progress.json') for k,r in reports.items()},capacityBefore=json.loads((work/'capacity-before.json').read_text()),finalObservation=observation,alertEvents=events,activeAlertsAtCloseout=0,limits=['Finite samples, not memory/CPU peaks, load test or SLA','SIGKILL is not power loss or host/Docker daemon restart','Linux VM not validated','Backup/independent-volume restore/release rollback belongs to B-06.6','D31/D35 historical review projections retained; no generic isolation cleanup','111 application JUnit tests passed after opaque rosterVersion parser fix; no new full browser suite; A/web and funds eligibility rules unchanged'],gitPublished=False)
 historytests=subprocess.run(['python','-B',ROOT/'docs/tests/test-b06-trade-work-history.py'],capture_output=True,text=True,encoding='utf-8');(work/'history-tests.log').write_text(historytests.stdout+historytests.stderr,encoding='utf-8');require(historytests.returncode==0 and 'Ran 3 tests' in historytests.stderr,'History classification tests failed')
 observertests=subprocess.run(['python','-B',ROOT/'docs/tests/test-b06-observability.py'],capture_output=True,text=True,encoding='utf-8');(work/'observer-tests.log').write_text(observertests.stdout+observertests.stderr,encoding='utf-8');require(observertests.returncode==0 and 'Ran 7 tests' in observertests.stderr,'Observer tests failed')
 newproof['observerHistoryClassification']={'decision':'B06-D44','relationalTests':3,'negativeTerminalOrBindingCases':30,'observerTests':7,'actualMySqlSelectOnlyTlsVerified':True,'historicalSettledHandoffs':observation['queues']['b_trade_work']['historicalSettledHandoffs'],'activeTradeWork':observation['queues']['b_trade_work']['pending'],'retainedOriginalRows':True,'scope':'Post-matrix observer-only correction; application images and business matrix sources unchanged'}
 extra=['docs/tests/collect-b06-faults.py','docs/tests/test-b06-faults.py','docs/tests/run-b06-interrupted-recovery.py','docs/tests/run-b06-runtime-gap.py','scripts/b06-observability.py','docs/tests/test-b06-observability.py','docs/tests/test-b06-trade-work-history.py'];newproof['sourceSha256'].update({f:sha(ROOT/f) for f in extra})
 before=json.loads((work/'final-drill-safety-before.json').read_text());docker=['docker','--context','desktop-linux']
 after={'hostsSha256':hashlib.sha256(Path('C:/Windows/System32/drivers/etc/hosts').read_bytes()).hexdigest(),'defaultDockerContext':subprocess.check_output(['docker','context','show'],text=True).strip(),'shared':subprocess.check_output(docker+['ps','-a','--filter','label=com.docker.compose.project!=zj-market-b06','--filter','label=b06.observer!=true','--filter','label=b06.fault-tool!=true','--format','{{.ID}} {{.Names}} {{.Image}} {{.State}}'],text=True),'networks':subprocess.check_output(docker+['network','ls','--filter','label=com.docker.compose.project=zj-market-b06','--format','{{.ID}} {{.Name}}'],text=True)}
 require(before==after,'Post-matrix recovery drill changed external/network scope');newproof['postDrillSafety']={'hostsUnchanged':True,'sharedContainersUnchanged':True,'projectNetworkIdentitiesUnchanged':True,'defaultDockerContext':after['defaultDockerContext'],'hostsSha256':after['hostsSha256']}
 # Reject publication if it would expose actual runtime secrets or demonstration passwords.
 serialized=json.dumps(newproof,ensure_ascii=False,indent=2)+'\n';secrets=json.loads((ROOT/'.local/b06/runtime/private/values.json').read_text()).values()
 accounts=json.loads((ROOT/'.local/b06/control/demo-accounts.json').read_text()).values()
 require(all(str(v) not in serialized for v in secrets),'Secret in public summary');require(all(v['password'] not in serialized for v in accounts),'Account password in public summary');require('PRIVATE KEY' not in serialized,'Private key in summary')
 (work/'acceptance.json').write_text(serialized,encoding='utf-8');(ROOT/'docs/tests/b06-fault-acceptance.json').write_text(serialized,encoding='utf-8');print('B065_PUBLIC_ACCEPTANCE_PASS checks='+str(len(business['checks'])))
if __name__=='__main__':main()
