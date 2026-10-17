"""Apply the frozen additive TD-01 A indexes to the empty UX-owned database."""
from pathlib import Path
import argparse
import hashlib
import importlib.util

EXPECTED_SHA256 = '76B31705BD78A8F277794B448D4F5C26F8907BEE070CF56948A0167F7526FD66'


def main(root: Path) -> None:
    root = root.resolve(strict=True)
    if root.name != 'zj-market-ux':
        raise RuntimeError('Refusing non-UX target')
    migration = root / 'deploy/ux/a-discovery-indexes.sql'
    data = migration.read_bytes()
    if hashlib.sha256(data).hexdigest().upper() != EXPECTED_SHA256:
        raise RuntimeError('A discovery migration hash mismatch')
    spec = importlib.util.spec_from_file_location('ux_deployment', root / 'scripts/b06-deployment.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.PROJECT != 'zj-market-ux':
        raise RuntimeError('UX deployment project mismatch')
    d = module.Deployment('desktop-linux')
    d.ownership()
    state = d.state()
    sql = ("SELECT COUNT(DISTINCT INDEX_NAME) FROM information_schema.STATISTICS "
           "WHERE TABLE_SCHEMA='group_buy_market_b06' AND INDEX_NAME IN "
           "('idx_ab_team_discovery','idx_ab_order_discovery_owner');")
    count = int(d.admin('ux-discovery-index-count', sql).strip())
    if count == 0:
        d.admin('ux-discovery-index-migration', 'USE group_buy_market_b06;\n' + data.decode('utf-8'))
    elif count != 2:
        raise RuntimeError('Partial A discovery indexes; manual review required')
    if int(d.admin('ux-discovery-index-verify', sql).strip()) != 2:
        raise RuntimeError('A discovery index verification failed')
    state['uxDiscoveryIndexSha256'] = EXPECTED_SHA256
    state['schemaFingerprint'] = d.fingerprint()
    d.save(state)
    d.ready()
    print('PASS UX-owned A discovery indexes and new schema fingerprint')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    main(p.parse_args().root)
