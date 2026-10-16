"""Tamper only a disposable relocated copy, then assert fail-closed config validation."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name('stable-controller.py')
spec = importlib.util.spec_from_file_location('stable_controller', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    root = parser.parse_args().root.resolve()
    if root.name != 'relocated-bundle' or not root.is_relative_to((WORKSPACE / 'target/stable-isolation').resolve()):
        raise RuntimeError('Only a disposable relocated bundle inside workspace may be changed')
    control = module.Controller(root)
    control.check_bundle()
    item = next(entry for entry in control.private_manifest['files']
                if entry['relativePath'].endswith('capabilities-open.properties'))
    file = (control.private_dir / item['relativePath']).resolve()
    if not file.is_relative_to(control.private_dir):
        raise RuntimeError('Test file escaped private bundle')
    file.write_bytes(file.read_bytes() + b'\n')
    try:
        control.check_bundle()
    except RuntimeError as error:
        if str(error).startswith('Private file drift'):
            print('PASS disposable configuration drift rejected')
            return
        raise
    raise RuntimeError('Configuration drift was not rejected')


if __name__ == '__main__':
    main()
