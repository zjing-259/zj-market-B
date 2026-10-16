"""Read-only funds, inventory and obligation evidence for ST-03."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path(__file__).with_name('st03-cutover.py')
spec = importlib.util.spec_from_file_location('st03_cutover', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.out.resolve()
    if root != module.STABLE.resolve() or not output.is_relative_to(
            (module.B / 'target/stable-isolation').resolve()):
        raise RuntimeError('Unexpected ST-03 evidence location')
    control = module.module.Controller(root)
    control.ready()
    data = module.data_snapshot(control)
    data['inventoryLedger'] = control.sql(
        'SELECT kind,COUNT(*) FROM zj_market_b06.b_inventory_ledger GROUP BY kind ORDER BY kind;').splitlines()
    data['simPaymentRows'] = int(control.sql('SELECT COUNT(*) FROM zj_market_b06.b_sim_payment;').strip())
    data['capturedAtUtc'] = datetime.now(timezone.utc).isoformat()
    module.write(output, data)
    print(json.dumps({'status': 'ST03_SNAPSHOT_PASS', 'output': str(output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
