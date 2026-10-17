"""Prepare the ST-04 worktree without touching the stable deployment.

Run once against a clean codex/storefront-ux worktree. Runtime secrets and
release.env remain under that worktree's ignored .local directory.
"""
from pathlib import Path
import argparse
import subprocess

ST01 = 'e18f4479dd934b58e93a183229110bd0b8803db3'
PROJECT = 'zj-market-ux'
HOST = 'zj-market-ux.test'


def replace_once(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding='utf-8')
    if source.count(old) != 1:
        raise RuntimeError(f'Expected one occurrence of {old!r} in {path}')
    path.write_text(source.replace(old, new), encoding='utf-8')


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def main(root: Path) -> None:
    root = root.resolve(strict=True)
    if root == Path(__file__).resolve().parents[1]:
        raise RuntimeError('Refusing to prepare the original B worktree')
    if git(root, 'branch', '--show-current') != 'codex/storefront-ux':
        raise RuntimeError('Target is not the UX branch')
    if git(root, 'rev-parse', 'HEAD') != ST01:
        raise RuntimeError('UX worktree is not at the frozen ST-01 commit')
    if git(root, 'status', '--porcelain'):
        raise RuntimeError('UX worktree already contains changes')
    compose = root / 'deploy/b06/compose.yml'
    replace_once(compose, 'name: zj-market-b06', f'name: {PROJECT}')
    replace_once(compose, '127.0.0.1}:443:8443', '127.0.0.1}:8446:8443')
    replace_once(compose, 'https://zj-market.test:8443/healthz', f'https://{HOST}:8443/healthz')
    replace_once(compose, 'zj-market.test:127.0.0.1', f'{HOST}:127.0.0.1')
    # The stable stack already consumes ~1.5 GiB. These limits total 3 GiB
    # and still exceed each service's measured stable usage.
    limits = compose.read_text(encoding='utf-8')
    for old, new in [('mem_limit: 768m', 'mem_limit: 512m'),
                     ('mem_limit: 768m', 'mem_limit: 512m'),
                     ('mem_limit: 256m', 'mem_limit: 128m'),
                     ('mem_limit: 384m', 'mem_limit: 256m'),
                     ('mem_limit: 1280m', 'mem_limit: 768m'),
                     ('mem_limit: 1024m', 'mem_limit: 768m')]:
        if old not in limits:
            raise RuntimeError(f'Missing expected UX resource limit: {old}')
        limits = limits.replace(old, new, 1)
    compose.write_text(limits, encoding='utf-8')
    network_tail = 'networks:\n  edge: {}\n  rpc:\n    internal: true\n  data:\n    internal: true\n  redis:\n    internal: true\n  mq:\n    internal: true\n'
    network_ux = 'networks:\n' + ''.join(
        f'  {name}:\n    internal: {str(name != "edge").lower()}\n    ipam:\n      config:\n        - subnet: 10.250.{50 + offset}.0/24\n'
        for offset, name in enumerate(('edge', 'rpc', 'data', 'redis', 'mq')))
    replace_once(compose, network_tail, network_ux)
    replace_once(root / 'scripts/b06-deployment.py', "PROJECT='zj-market-b06'", f"PROJECT='{PROJECT}'")
    capacity = root / 'scripts/b06-deployment.py'
    replace_once(capacity, "int(4.5*GIB)", "int(3*GIB)")
    replace_once(capacity, "4.75*GIB", "3.25*GIB")
    replace_once(capacity, "(4.75GiB)", "(3.25GiB)")
    replace_once(root / 'scripts/prepare-b06-secrets.py', "issue('web',['zj-market.test'])", f"issue('web',['{HOST}'])")
    replace_once(root / 'deploy/b06/config/b.properties', 'b.identity.origin=https://zj-market.test', f'b.identity.origin=https://{HOST}:8446')
    replace_once(root / 'deploy/b06/nginx.conf', 'server_name zj-market.test;', f'server_name {HOST};')
    client = root / 'docs/tests/b06-startup-client.mjs'
    source = client.read_text(encoding='utf-8').replace('zj-market.test', HOST).replace('port:443', 'port:8446').replace('zj-market-b06_edge', f'{PROJECT}_edge')
    source = source.replace(f'https://{HOST}', f'https://{HOST}:8446')
    client.write_text(source, encoding='utf-8')
    private = root / '.local/b06/build'
    private.mkdir(parents=True, exist_ok=True)
    image = {
        'B06_A_IMAGE': 'sha256:48c7af4be50e59133cf76aac69bac7142fb0ab19c27c4cf21ae352550dc57ddc',
        'B06_B_IMAGE': 'sha256:cebd526685cd3b2bba6619494321abae36a6f5df976306a67f08549d781d196a',
        'B06_WEB_IMAGE': 'zj-market-ux/web:st04-20261017-01',
        'B06_SECRET_DIR': str(root / '.local/b06/runtime').replace('\\', '/'),
        'B06_BIND_IP': '127.0.0.1',
        'B06_ADMISSION_FILE': str(root / 'deploy/b06/config/admission-maintenance.conf').replace('\\', '/'),
    }
    (private / 'release.env').write_text(''.join(f'{key}={value}\n' for key, value in image.items()), encoding='utf-8')
    print('Prepared isolated UX source and private release inputs; secrets not generated.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    main(parser.parse_args().root)
