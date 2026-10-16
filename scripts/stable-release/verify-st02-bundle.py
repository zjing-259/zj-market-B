"""Static verification of the generated independent ST-02 runtime bundle."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path

SOURCE = Path(__file__).with_name('stable-controller.py')
spec = importlib.util.spec_from_file_location('stable_controller', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def verify(root: Path) -> dict:
    control = module.Controller(root)
    control.check_bundle()
    release = control.release
    if len(control.private_manifest['files']) != 37:
        raise RuntimeError('Unexpected private input count')
    if any(item.get('source') for item in control.private_manifest['files']):
        raise RuntimeError('Original source paths retained in runtime manifest')
    host_path = re.compile(rb'[A-Za-z]:[/\\](?:Java|Users)[/\\]')
    for item in control.private_manifest['files']:
        if item['bytes'] < 1_000_000 and host_path.search(
                (control.private_dir / item['relativePath']).read_bytes()):
            raise RuntimeError('Host absolute path in copied runtime input')
    for mode in ('on', 'maintenance'):
        raw = (control.root / release['templates'][mode]['file']).read_text(encoding='utf-8')
        if re.search(r'D:[/\\]Java|group-buy-market|zj-market-b-06|"build"\s*:', raw, re.I):
            raise RuntimeError('Development tree or build instruction in Compose template')
        config = control.rendered(mode)
        if set(config['services']) != set(module.SERVICES) | {'mq-permissions'}:
            raise RuntimeError('Unexpected Compose services')
        if any(item.get('external') is not True for item in config['volumes'].values()):
            raise RuntimeError('Data volume may be created implicitly')
        if any(item.get('external') is not True for item in config['networks'].values()):
            raise RuntimeError('Network may be created implicitly')
        for name, service in config['services'].items():
            if 'build' in service or service['image'] != release['images'][release['serviceImageRoles'][name]]:
                raise RuntimeError('Unpinned service image: ' + name)
            for mount in service.get('volumes', []):
                if mount.get('type') == 'bind' and not Path(mount['source']).resolve().is_relative_to(control.private_dir):
                    raise RuntimeError('External bind source: ' + name)
        for secret in config['secrets'].values():
            if not Path(secret['file']).resolve().is_relative_to(control.private_dir):
                raise RuntimeError('External secret source')
    for name in ('controller.py', 'stable-probe.mjs', 'stable.ps1', 'open-stable.ps1'):
        source = (control.release_dir / name).read_text(encoding='utf-8')
        if re.search(r'D:[/\\]Java[/\\](?:group-buy-market|zj-market-b-06)', source, re.I):
            raise RuntimeError('Old tree read in runtime tool: ' + name)
    return {'status': 'ST02_BUNDLE_STATIC_PASS', 'privateFiles': 37,
            'fixedServices': 7, 'externalVolumes': len(release['volumes']),
            'externalNetworks': len(release['networks']), 'noOldTreeReads': True}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.root), ensure_ascii=False))


if __name__ == '__main__':
    main()
