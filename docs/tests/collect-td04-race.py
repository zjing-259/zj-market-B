"""Verify a TD-04 last-slot race against isolated A/B/channel SQL facts."""
from pathlib import Path
from decimal import Decimal
import argparse, datetime, hashlib, json, re, subprocess

ROOT = Path(__file__).resolve().parents[2]
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'td04_[0-9]{8}_[0-9]{2}', args.run_name): raise RuntimeError('Invalid run name')
    work = ROOT / 'target/team-discovery' / args.run_name
    race = json.loads((work / 'race-race-report.json').read_text())
    if race['status'] != 'PASSED': raise RuntimeError('Race not passed')
    project = 'zj-market-' + args.run_name.replace('_', '-')
    docker = ['docker', '--context', 'desktop-linux']
    def sql(query):
        result = subprocess.run(docker + ['exec', '-i', project + '-mysql-1', 'sh', '-c',
            'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names'],
            input=query, capture_output=True, text=True, timeout=60)
        if result.returncode: raise RuntimeError('Isolated SQL query failed: ' + result.stderr[-500:])
        return result.stdout.strip()
    def row(query): return json.loads(sql(query))
    team, goods = race['teamId'], race['goodsId']
    ids = [race['orders']['open'], race['orders']['winner'], *race['orders']['losers']]
    if not all(re.fullmatch(r'[a-f0-9-]{36}', x) for x in [team, goods, *ids]): raise RuntimeError('Bad identifier')
    checks = []
    inv = row(f"SELECT JSON_OBJECT('available',available,'reserved',reserved,'sold',sold) FROM zj_market_b06.b_inventory_account WHERE goods_id='{goods}';")
    assert inv == {'available':8,'reserved':0,'sold':2}, inv
    checks.append('one-open-one-join-stock-conservation')
    a_team = row(f"SELECT JSON_OBJECT('status',team_status,'target',target_count,'paid',paid_count,'reserved',reserved_count) FROM group_buy_market_b06.ab_team WHERE team_id='{team}';")
    assert a_team == {'status':'COMPLETED','target':2,'paid':2,'reserved':2}, a_team
    checks.append('A-exact-team-quota')
    facts = {}
    for order_id in ids:
        winning = order_id in ids[:2]
        b = row(f"SELECT JSON_OBJECT('status',o.business_status,'requestedTeam',JSON_UNQUOTE(JSON_EXTRACT(o.reserve_request,'$.teamId')),'reservation',r.state,'confirmLedgers',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='CONFIRM'),'releaseLedgers',(SELECT COUNT(*) FROM zj_market_b06.b_inventory_ledger l WHERE l.order_id=o.order_id AND l.kind='RELEASE'),'payments',(SELECT COUNT(*) FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id AND p.funds_state='SUCCEEDED' AND p.a_acceptance='ACCEPTED'),'paidAmount',(SELECT COALESCE(SUM(p.amount),0) FROM zj_market_b06.b_payment p WHERE p.order_id=o.order_id AND p.funds_state='SUCCEEDED'),'refundAmount',(SELECT COALESCE(SUM(rf.amount),0) FROM zj_market_b06.b_refund rf WHERE rf.order_id=o.order_id AND rf.funds_status='SUCCEEDED'),'fulfillment',(SELECT COUNT(*) FROM zj_market_b06.b_fulfillment f WHERE f.order_id=o.order_id AND f.status='PENDING')) FROM zj_market_b06.b_market_order o JOIN zj_market_b06.b_inventory_reservation r ON r.order_id=o.order_id WHERE o.order_id='{order_id}';")
        assert b['requestedTeam'] in (None,team,'null'), b
        if winning:
            assert b['status']=='GROUP_COMPLETED' and b['reservation']=='CONFIRMED', b
            assert b['confirmLedgers']==b['payments']==b['fulfillment']==1 and b['releaseLedgers']==0, b
            assert Decimal(str(b['paidAmount']))==90 and Decimal(str(b['refundAmount']))==0, b
        else:
            assert b['status']=='CLOSED' and b['reservation']=='RELEASED', b
            assert b['confirmLedgers']==b['payments']==b['fulfillment']==0 and b['releaseLedgers']==1, b
            assert Decimal(str(b['paidAmount']))==Decimal(str(b['refundAmount']))==0, b
        a = sql(f"SELECT CONCAT(order_status,'|',IFNULL(payment_id,'')) FROM group_buy_market_b06.ab_trade_order WHERE source='b06' AND channel='web' AND out_trade_no='{order_id}';")
        if winning: assert a.startswith('PAID|') and len(a.split('|')[1])>0, a
        else: assert a in ('','CANCELLED|','EXPIRED|'), a
        channel = row(f"SELECT JSON_OBJECT('paidRoots',(SELECT COUNT(*) FROM zj_market_b06.b_sim_payment s JOIN zj_market_b06.b_payment p ON p.payment_id=s.payment_id WHERE p.order_id='{order_id}' AND s.gate='PAID'),'successfulAttempts',(SELECT COUNT(*) FROM zj_market_b06.b_sim_attempt sa JOIN zj_market_b06.b_payment p ON p.payment_id=sa.payment_id WHERE p.order_id='{order_id}' AND sa.state='SUCCEEDED'));")
        assert channel['paidRoots']==channel['successfulAttempts']==(1 if winning else 0), channel
        checks.append(('winner' if winning else 'loser')+'-funds-stock-A-'+order_id)
        facts[order_id]={'B':b,'A':a,'channel':channel}
    containers=json.loads(subprocess.check_output(docker+['inspect']+[project+'-'+x+'-1' for x in ['mysql','redis','namesrv','broker','marketing-a','market-b','web']],text=True))
    assert all(c['State']['Health']['Status']=='healthy' and not c['State']['OOMKilled'] for c in containers)
    checks.append('seven-services-healthy')
    out={'stage':'TD-04','status':'PASSED_REAL_RACE_ACCOUNTING_SUBSET','stageCompletion':False,'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'team':a_team,'inventory':inv,'orders':facts,'raceReportSha256':hashlib.sha256((work/'race-race-report.json').read_bytes()).hexdigest()}
    (work/'race-accounting-report.json').write_text(json.dumps(out,indent=2)+'\n')
    print('PASS TD04 race accounting subset')
if __name__=='__main__': main()
