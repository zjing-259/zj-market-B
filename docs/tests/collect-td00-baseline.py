"""Freeze source, old artifacts and migrations before TD changes. No business writes."""
import argparse
import hashlib
import io
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, encoding='utf-8').strip()


def collect(a, deployed, output):
    output.mkdir(parents=True, exist_ok=False)
    report = {'stage': 'TD-00', 'capturedAt': datetime.now(timezone.utc).isoformat(), 'repositories': {}}
    for name, root in [('a', a), ('b', ROOT), ('b06', deployed)]:
        tracked = git(root, 'ls-files').splitlines()
        report['repositories'][name] = {
            'path': str(root), 'head': git(root, 'rev-parse', 'HEAD'),
            'branch': git(root, 'branch', '--show-current'), 'status': git(root, 'status', '--short'),
            'sourceSha256': {p: sha((root/p).read_bytes()) for p in tracked
                             if p.endswith(('.java', '.sql')) or p.endswith('pom.xml')},
        }
    report['artifacts'] = []
    candidates = [('a-legacy-source', a/'group-buy-market-app/target/group-buy-market-app.jar'),
                  ('a-b06', deployed/'.local/b06/build/a/app.jar'),
                  ('b-b06', deployed/'.local/b06/build/b/app.jar')]
    contracts = []
    for label, path in candidates:
        data = path.read_bytes()
        frozen = output/'artifacts'/label/'app.jar'
        frozen.parent.mkdir(parents=True)
        frozen.write_bytes(data)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            entry = next(n for n in z.namelist() if n.startswith('BOOT-INF/lib/group-buy-market-contract-'))
            contract = z.read(entry)
            (frozen.parent/'contract.jar').write_bytes(contract)
            contracts.append(contract)
        report['artifacts'].append({'label': label, 'path': str(path), 'sha256': sha(data),
                                    'bytes': len(data), 'embeddedContract': entry, 'contractSha256': sha(contract)})
    assert contracts[1] == contracts[2], 'Deployed A/B embedded contracts differ'
    report['deployedContractsIdentical'] = True
    release = json.loads((ROOT/'docs/b06-final-release.json').read_text())
    report['expectedImages'] = release['allRuntimeImages']
    report['releaseSha256'] = sha((ROOT/'docs/b06-final-release.json').read_bytes())
    report['runtime'] = runtime(release['allRuntimeImages'])
    (output/'baseline.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'artifacts': len(candidates), 'deployedContractsIdentical': True,
                      'runtime': report['runtime']['status'], 'output': str(output)}, ensure_ascii=False))


def runtime(expected):
    args = ['docker', '--context', 'desktop-linux']
    r = subprocess.run(args+['ps', '-a', '--filter', 'label=com.docker.compose.project=zj-market-b06',
                            '--format', '{{.Names}}'], capture_output=True, text=True, timeout=30)
    if r.returncode:
        return {'status': 'ENGINE_UNAVAILABLE', 'imagesVerified': False}
    names = r.stdout.splitlines()
    rows = json.loads(subprocess.check_output(args+['inspect']+names, text=True, encoding='utf-8')) if names else []
    # Deliberately omit environment variables, mounts and all other private inspect fields.
    services = {x['Config']['Labels']['com.docker.compose.service']:
                {'image': x['Image'], 'running': x['State']['Running'],
                 'health': x['State'].get('Health', {}).get('Status')} for x in rows}
    # Compose retains its successful one-shot ACL initializer; it is not an eighth runtime service.
    extra = set(services) - set(expected)
    matches = (set(expected) <= set(services) and extra <= {'mq-permissions'}
               and all(services[s]['image'] == i for s, i in expected.items()))
    return {'status': 'PINNED_IMAGES_MATCH' if matches else 'RUNTIME_MISMATCH',
            'imagesVerified': matches, 'services': services}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--a-root', type=Path, required=True)
    p.add_argument('--deployed-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    collect(a.a_root, a.deployed_root, a.output)
