"""Read-only main443 conservation and original-obligation retention for TD-06.3."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / 'target/team-discovery/td06_3_main_20261016_01'


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    baseline = load_module('td06_baseline', ROOT / 'docs/tests/collect-td06-baseline.py')
    before = json.loads((BATCH / 'before.json').read_text(encoding='utf-8'))
    accounting = json.loads((BATCH / 'browser/accounting-report.json').read_text(encoding='utf-8'))
    after = {'business': baseline.status_snapshot('zj-market-b06'),
             'obligations': baseline.obligation_snapshot('zj-market-b06')}
    (BATCH / 'after.json').write_text(json.dumps(after, indent=2) + '\n', encoding='utf-8')
    retention = {}
    for category, original in before['obligations'].items():
        original_keys = {item['keySha256'] for item in original}
        current_keys = {item['keySha256'] for item in after['obligations'][category]}
        missing = original_keys - current_keys
        retention[category] = {'before': len(original_keys), 'after': len(current_keys),
                               'originalKeysMissingFromActiveSet': len(missing)}
        if missing:
            raise RuntimeError(f'Original obligation changed active state: {category}; inspect private snapshots before concluding')
    money_before = before['business']['bChannelMoney']
    money_after = after['business']['bChannelMoney']
    paid_delta = Decimal(money_after['paidAmount']) - Decimal(money_before['paidAmount'])
    refunded_delta = Decimal(money_after['refundedAmount']) - Decimal(money_before['refundedAmount'])
    if (paid_delta, refunded_delta) != (Decimal('270.00'), Decimal('90.00')):
        raise RuntimeError('Unexpected main443 channel money delta')
    stock_before = before['business']['bInventory']
    stock_after = after['business']['bInventory']
    stock_delta = {key: stock_after[key] - stock_before[key] for key in ('available', 'reserved', 'sold')}
    if stock_delta != {'available': 28, 'reserved': 0, 'sold': 2}:
        raise RuntimeError('Unexpected main443 stock delta')
    if accounting['status'] != 'PASSED_REAL_BROWSER_ACCOUNTING_SUBSET':
        raise RuntimeError('Per-order accounting did not pass')
    report = {
        'stage': 'TD-06.3', 'status': 'PASSED_MAIN443_CONSERVATION',
        'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
        'target': 'zj-market-b06 main HTTPS 443',
        'browserCheckCount': len(accounting['browserChecks']),
        'perOrderAccountingCheckCount': len(accounting['accountingChecks']),
        'channelMoneyBefore': money_before, 'channelMoneyAfter': money_after,
        'channelPaidDelta': str(paid_delta), 'channelRefundedDelta': str(refunded_delta),
        'inventoryBefore': stock_before, 'inventoryAfter': stock_after,
        'inventoryDelta': stock_delta, 'originalObligationRetention': retention,
        'privateEvidenceSha256': {
            name: hashlib.sha256((BATCH / name).read_bytes()).hexdigest()
            for name in ('before.json', 'browser/browser-report.json',
                         'browser/accounting-report.json', 'after.json')},
        'scope': 'Fresh main443 browser transactions and read-only A/B/channel accounting; no TD-04 fault matrix rerun',
        'gitPublished': False,
    }
    output = ROOT / 'docs/tests/td06-3-acceptance.json'
    if output.exists():
        raise RuntimeError('Acceptance summary already exists; preserve original evidence')
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS TD-06.3 main443 channel, stock and original obligation retention')


if __name__ == '__main__':
    main()
