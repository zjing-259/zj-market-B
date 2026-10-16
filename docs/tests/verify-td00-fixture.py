"""Read-only verification of prepared TD00 data and unchanged query snapshots."""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def main(args):
    spec=importlib.util.spec_from_file_location('td00_prepare',ROOT/'docs/tests/prepare-td00-fixture.py')
    f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
    facts=json.loads(args.fixture.read_text())
    schemas=list(facts['schemas'])
    assert len(schemas)==2 and all(re.fullmatch(r'(group_buy_market|zj_market)_td00_[0-9]{8}_[0-9]{2}',d) for d in schemas)
    a=next(d for d in schemas if d.startswith('group_buy_market_'));b=next(d for d in schemas if d.startswith('zj_market_'))
    before={d:f.fingerprint(d) for d in schemas}
    outputs={}
    for label,db in [('a',a),('b',b)]:
        sql=(ROOT/f'docs/tests/td00/read-only-{label}.sql').read_text()
        outputs[label]=f.sql(f'USE `{db}`;\n'+sql)
    checks={}
    checks['four_enabled_new_accounts']=f.sql(f'SELECT COUNT(*) FROM `{b}`.b_user WHERE enabled=1;').strip()=='4'
    checks['correct_argon2_parameters']=f.sql(f"SELECT COUNT(*) FROM `{b}`.b_user WHERE password_hash LIKE '{{argon2id}}$argon2id$v=19$m=19456,t=2,p=1$%';").strip()=='4'
    checks['roles']=f.sql(f'SELECT COUNT(*) FROM `{b}`.b_user_role;').strip()=='5'
    checks['stock_and_original_inbound_only']=f.sql(f'SELECT available,reserved,sold,(SELECT COUNT(*) FROM `{b}`.b_inventory_ledger) FROM `{b}`.b_inventory_account;').strip()=='100\t0\t0\t1'
    checks['new_activity_usable_window']=f.sql(f'SELECT COUNT(*) FROM `{a}`.group_buy_activity WHERE status=1 AND target=3 AND valid_time=120 AND start_time<=UTC_TIMESTAMP() AND end_time>UTC_TIMESTAMP()+INTERVAL 2 DAY;').strip()=='1'
    checks['no_fabricated_product_sync']=f.sql(f'SELECT (SELECT COUNT(*) FROM `{b}`.b_product_outbox)+(SELECT COUNT(*) FROM `{b}`.b_product_sync)+(SELECT COUNT(*) FROM `{a}`.ab_product_projection);').strip()=='0'
    for db,table in [(a,'ab_team'),(a,'ab_trade_order'),(a,'ab_outbox'),(b,'b_market_order'),(b,'b_purchase_confirmation'),(b,'b_inventory_reservation'),(b,'b_payment'),(b,'b_sim_payment'),(b,'b_refund'),(b,'b_fulfillment')]:
        checks['empty_'+table]=f.sql(f'SELECT COUNT(*) FROM `{db}`.`{table}`;').strip()=='0'
    after={d:f.fingerprint(d) for d in schemas}
    checks['queries_leave_fixture_bytes_identical']=before==after
    release=json.loads((ROOT/'docs/b06-final-release.json').read_text())
    runtime=__import__('runpy').run_path(str(ROOT/'docs/tests/collect-td00-baseline.py'))['runtime'](release['allRuntimeImages'])
    checks['actual_seven_runtime_images_match']=runtime['imagesVerified']
    checks['seven_runtime_services_healthy']=all(runtime['services'][s]['running'] and runtime['services'][s]['health']=='healthy' for s in release['allRuntimeImages'])
    baseline=json.loads((args.baseline/'baseline.json').read_text())
    actual={}
    for label,service in [('a-b06','marketing-a'),('b-b06','market-b')]:
        observed=subprocess.check_output(f.DOCKER+['exec','zj-market-b06-'+service+'-1','sha256sum','/app/app.jar'],text=True).split()[0].upper()
        expected=next(x['sha256'] for x in baseline['artifacts'] if x['label']==label)
        actual[service]=observed
        checks['actual_'+service+'_jar_matches_frozen']=observed==expected
    report={'stage':'TD-00','status':'PASSED_PREPARED_FIXTURE_AND_READONLY_BASELINE' if all(checks.values()) else 'FAILED',
            'checks':checks,'count':len(checks),'fixture':str(args.fixture),'before':before,'after':after,
            'snapshotOutputs':outputs,'runtime':runtime,'actualJarSha256':actual,
            'limitations':['DDL-cloned fixture; Flyway history empty, not migration acceptance','No discovery RPC or HTTP endpoint implemented','No fixture product MQ sync or accepted payment claimed']}
    if args.output.exists():raise ValueError('Fresh output required')
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    assert all(checks.values()), 'Failed checks preserved in output'
    print(json.dumps({'status':report['status'],'checks':len(checks),'output':str(args.output)}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    main(p.parse_args())
