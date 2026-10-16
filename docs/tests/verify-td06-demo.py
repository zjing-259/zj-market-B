"""Read-only check that the isolated demo is still payable/joinable after restart."""
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'target/team-discovery/td06_demo_20261015_03'
REPORT = json.loads((WORK / 'demo-report.json').read_text(encoding='utf-8'))
if REPORT['status'] != 'PASSED_CANDIDATE_DEMO_READY':
    raise RuntimeError('Demo not prepared')
goods, team = REPORT['goodsId'], REPORT['teamId']
if not all(re.fullmatch(r'[0-9a-f-]{36}', value) for value in (goods, team)):
    raise RuntimeError('Invalid isolated demo identity')
command = ['docker', '--context', 'desktop-linux', 'exec', '-i',
           'zj-market-td05-20261015-01-mysql-1', 'sh', '-c',
           'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --skip-column-names']
sql = f"""SELECT team_status,reserved_count,paid_count,target_count,(valid_end_time>UTC_TIMESTAMP(3))
FROM group_buy_market_b06.ab_team WHERE team_id='{team}';
SELECT COUNT(*) FROM zj_market_b06.b_payment p JOIN zj_market_b06.b_market_order o ON o.order_id=p.order_id
WHERE o.goods_id='{goods}' AND p.funds_state='SUCCEEDED' AND p.a_acceptance='ACCEPTED';"""
run = subprocess.run(command, input=sql, capture_output=True, text=True, encoding='utf-8',
                     errors='replace', timeout=60)
if run.returncode:
    raise RuntimeError('Candidate demo SQL check failed')
rows = run.stdout.strip().splitlines()
if len(rows) != 2:
    raise RuntimeError('Demo team/payment facts missing')
state, reserved, paid, target, future = rows[0].split('\t')
if state != 'FORMING' or not 1 <= int(paid) <= int(reserved) < int(target) or future != '1' or rows[1] != '1':
    raise RuntimeError('Demo no longer discoverable; prepare a new batch through normal business flow')
print(json.dumps({'status': 'DEMO_JOINABLE', 'target': 'candidate8445', 'goodsId': goods,
                  'teamId': team, 'expiresAt': REPORT['teamExpiresAt'],
                  'checkedAtUtc': datetime.now(timezone.utc).isoformat()}, ensure_ascii=False))
