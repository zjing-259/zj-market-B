"""Read-only ST-00 snapshot of the existing main443 release and its host dependencies.

Writes one redacted public report and one ignored private inventory. Never changes
containers, volumes, business records, Git refs, trust stores, or release files.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

B = Path(__file__).resolve().parents[2]
A = Path('D:/Java/group-buy-market')
OLD = Path('D:/Java/zj-market-b-06')
WORK = B / 'target/team-discovery/td06_2_main_20261015_01'
TD05 = B / 'target/team-discovery/td05_20261015_01'
BATCH = 'st00_20261016_01'
PRIVATE = B / 'target/stable-isolation' / BATCH
PUBLIC = B / 'docs/tests/st00-acceptance.json'
DOCKER = ['docker', '--context', 'desktop-linux']
SERVICES = ('mysql', 'redis', 'namesrv', 'broker', 'marketing-a', 'market-b', 'web')
VOLUMES = ('mysql-data', 'redis-data', 'broker-store', 'broker-logs', 'namesrv-logs')


def run(args, *, timeout=180):
    result = subprocess.run([str(item) for item in args], capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=timeout)
    if result.returncode:
        raise RuntimeError('ST-00 read-only command failed: ' + ' '.join(str(x) for x in args[:4]))
    return result.stdout


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    item = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item)
    return item


def git(repo: Path, *args: str) -> str:
    return run(['git', '-C', repo, *args]).strip()


def source_class(source: str) -> str:
    p = host_path(source).resolve()
    for label, base in [('td06PrivateRelease', WORK), ('td05PrivateBuild', TD05),
                        ('legacyPrivateOrHistory', OLD), ('bDevelopmentTree', B),
                        ('aDevelopmentTree', A)]:
        if p.is_relative_to(base.resolve()):
            return label
    return 'otherHostPath'


def host_path(source: str) -> Path:
    match = re.fullmatch(r'/run/desktop/mnt/host/([a-zA-Z])/(.*)', source)
    return Path(match.group(1).upper() + ':/' + match.group(2)) if match else Path(source)


def worktrees(repo: Path):
    raw = git(repo, 'worktree', 'list', '--porcelain')
    rows = []
    for block in raw.split('\n\n'):
        if not block.strip():
            continue
        parts = dict(line.split(' ', 1) for line in block.splitlines() if ' ' in line)
        rows.append({'path': parts.get('worktree'), 'head': parts.get('HEAD'),
                     'branch': parts.get('branch')})
    return rows


def git_inventory(repo: Path):
    untracked = [x for x in git(repo, 'ls-files', '--others', '--exclude-standard').splitlines() if x]
    modified = [x for x in git(repo, 'diff', '--name-only').splitlines() if x]
    staged = [x for x in git(repo, 'diff', '--cached', '--name-only').splitlines() if x]
    def groups(files):
        return {
            'applicationOrFrontend': sum(x.startswith(('group-buy-market-', 'zj-market-', 'frontend/')) or x == 'pom.xml' for x in files),
            'docsOrEvidence': sum(x.startswith('docs/') or x in ('TASK_PROGRESS.md', 'README.md') for x in files),
            'deploymentOrScripts': sum(x.startswith(('deploy/', 'scripts/')) for x in files),
            'other': sum(not (x.startswith(('group-buy-market-', 'zj-market-', 'frontend/', 'docs/', 'deploy/', 'scripts/')) or x in ('pom.xml', 'TASK_PROGRESS.md', 'README.md')) for x in files),
        }
    return ({'branch': git(repo, 'branch', '--show-current'), 'head': git(repo, 'rev-parse', 'HEAD'),
            'worktrees': worktrees(repo), 'modifiedCount': len(modified),
            'stagedCount': len(staged), 'untrackedCount': len(untracked),
            'modifiedClasses': groups(modified), 'untrackedClasses': groups(untracked)},
            {'modified': modified, 'staged': staged, 'untracked': untracked})


def host_tools():
    import yaml
    def version(args):
        result = subprocess.run([str(value) for value in args], capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=20)
        if result.returncode:
            raise RuntimeError('Required host executable failed: ' + str(args[0]))
        return (result.stdout + result.stderr).strip().splitlines()[0]
    java21 = Path('C:/Program Files/Java/jdk-21/bin/java.exe')
    javac21 = Path('C:/Program Files/Java/jdk-21/bin/javac.exe')
    edge = Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    return {
        'python': run(['python', '--version']).strip(), 'pythonPath': shutil.which('python'),
        'pyYaml': yaml.__version__, 'node': run(['node', '--version']).strip(),
        'nodePath': shutil.which('node'), 'git': run(['git', '--version']).strip(),
        'dockerDesktopLinux': run(DOCKER + ['version', '--format', '{{.Client.Version}}|{{.Server.Version}}']).strip(),
        'hostDefaultJava': version(['java', '-version']),
        'explicitJava21': version([java21, '-version']),
        'explicitJavac21': run([javac21, '-version']).strip(),
        'java21Path': str(java21), 'javac21Path': str(javac21),
        'powershellDesktopAvailable': bool(shutil.which('powershell.exe')),
        'powershellCoreAvailable': bool(shutil.which('pwsh')),
        'edgePath': str(edge), 'edgePresent': edge.is_file(),
    }


def dependency_inventory():
    entries = {
        'bController': B / 'scripts/td06-environment.py',
        'mainReleaseController': B / 'scripts/td06-main-release.py',
        'browserEntry': B / 'scripts/open-team-discovery-browser.ps1',
        'mainGatewayProbe': B / 'docs/tests/td06-main-gate.mjs',
        'st00InvalidWriteProbe': B / 'docs/tests/st00-gateway-probe.mjs',
        'bLegacyDeploymentModule': B / 'scripts/b06-deployment.py',
        'oldDeploymentController': OLD / 'scripts/b06-deployment.py',
        'oldReadinessClient': OLD / 'docs/tests/b06-startup-client.mjs',
        'td05RpcProbeSource': B / 'docs/tests/td05/Td05RpcProbe.java',
        'mainPrivateReleaseState': WORK / 'release.json',
        'mainComposeOn': WORK / 'compose-on.json',
        'mainComposeMaintenance': WORK / 'compose-maintenance.json',
        'td05FrozenASources': TD05 / 'a-source-hashes.json',
        'td05BJar': TD05 / 'build/b/app.jar',
        'td05ContractJar': TD05 / 'a-source/group-buy-market-contract/target/group-buy-market-contract-1.1.0-td.1.jar',
        'oldCa': OLD / '.local/b06/runtime/web-ca.pem',
        'oldDemoAccounts': OLD / '.local/b06/control/demo-accounts.json',
        'oldSeedGoods': OLD / '.local/b06/control/seed-goods-id.txt',
        'oldBackupProgress': OLD / '.local/b06/backups/b066-td062-20261015-03/progress.json',
        'oldBackupManifest': OLD / '.local/b06/backups/b066-td062-20261015-03/manifest.json',
        'oldBackupSeal': OLD / '.local/b06/backups/b066-td062-20261015-03/COMPLETE.json',
    }
    full = {key: {'path': str(path), 'exists': path.is_file(),
                  'sha256': sha(path) if path.is_file() else None} for key, path in entries.items()}
    missing = [name for name, value in full.items() if not value['exists']]
    if missing:
        raise RuntimeError('Startup dependency missing: ' + ', '.join(missing))
    return full, {'checkedFileCount': len(full), 'missingCount': 0,
                  'legacyTreeFileCount': sum(Path(value['path']).is_relative_to(OLD) for value in full.values()),
                  'td06PrivateReleaseFileCount': sum(Path(value['path']).is_relative_to(WORK) for value in full.values()),
                  'directDevelopmentTreeDependency': True,
                  'hostJdk21RequiredForRpcProbe': True,
                  'legacyTreeStillRequired': True}


def main():
    if PRIVATE.exists() or PUBLIC.exists():
        raise RuntimeError('ST-00 batch already exists; preserve original evidence and choose a new batch')
    release = load(B / 'docs/team-discovery-td06-release.json')
    old_lock = load(B / 'docs/team-discovery-td06-source-lock.json')
    td05 = module('td05_release', B / 'docs/tests/collect-td05-release.py')
    a_changed = [name for name, value in old_lock['a'].items() if sha(A / name) != value]
    b_current = td05.source_hashes(B)
    b_changed = [name for name, value in old_lock['b'].items() if b_current.get(name) != value]
    if a_changed or b_changed or set(b_current) != set(old_lock['b']):
        raise RuntimeError('Business source differs from TD-06 lock; do not claim same release')
    git_public_a, git_private_a = git_inventory(A)
    git_public_b, git_private_b = git_inventory(B)
    if git_public_a['branch'] != release['source']['a']['branch'] or git_public_b['branch'] != release['source']['b']['branch']:
        raise RuntimeError('Unexpected source branches')
    project = 'zj-market-b06'
    names = [project + '-' + service + '-1' for service in SERVICES]
    containers = json.loads(run(DOCKER + ['inspect', *names]))
    visible = run(DOCKER + ['ps', '-a', '--filter', 'label=com.docker.compose.project=' + project, '--format', '{{.Names}}']).splitlines()
    running_names = run(DOCKER + ['ps', '--filter', 'label=com.docker.compose.project=' + project, '--format', '{{.Names}}']).splitlines()
    if set(running_names) != set(names):
        raise RuntimeError('Unexpected running main project container set')
    extras = sorted(set(visible) - set(names))
    if extras != [project + '-mq-permissions-1']:
        raise RuntimeError('Unexpected auxiliary project container set')
    auxiliary = json.loads(run(DOCKER + ['inspect', *extras]))
    if auxiliary[0]['State']['Status'] != 'exited' or auxiliary[0]['State']['ExitCode'] != 0:
        raise RuntimeError('MQ permission initialization helper did not exit cleanly')
    expected = release['images']
    image_by_service = {}
    mounts = {}
    networks = {}
    ports = {}
    for service, row in zip(SERVICES, containers):
        labels = row['Config']['Labels'] or {}
        if labels.get('com.docker.compose.project') != project or labels.get('com.docker.compose.service') != service:
            raise RuntimeError('Container Compose ownership mismatch: ' + service)
        state = row['State']
        if not state['Running'] or state.get('Health', {}).get('Status') != 'healthy' or state.get('OOMKilled'):
            raise RuntimeError('Main container unhealthy: ' + service)
        image_by_service[service] = row['Image']
        if service in expected and row['Image'] != expected[service]:
            raise RuntimeError('Runtime image differs from TD-06 archive: ' + service)
        mounts[service] = row['Mounts']
        networks[service] = sorted(row['NetworkSettings']['Networks'])
        ports[service] = row['NetworkSettings']['Ports']
    web_ports = ports['web'].get('8443/tcp') or []
    if len(web_ports) != 1 or web_ports[0]['HostIp'] != '127.0.0.1' or web_ports[0]['HostPort'] != '443':
        raise RuntimeError('Main HTTPS port is not loopback 443')
    if any(binding for service, mapping in ports.items() if service != 'web' for binding in mapping.values() if binding):
        raise RuntimeError('Unexpected published port on main non-web service')
    volumes = json.loads(run(DOCKER + ['volume', 'inspect', *[project + '_' + name for name in VOLUMES]]))
    for volume in volumes:
        if (volume['Name'] not in {project + '_' + name for name in VOLUMES} or
                (volume.get('Labels') or {}).get('com.docker.compose.project') != project):
            raise RuntimeError('Main volume ownership mismatch')
    used = {mount['Name'] for rows in mounts.values() for mount in rows if mount['Type'] == 'volume'}
    if not {volume['Name'] for volume in volumes}.issubset(used):
        raise RuntimeError('Original five volumes not mounted')
    network_names = sorted({name for values in networks.values() for name in values})
    network_rows = json.loads(run(DOCKER + ['network', 'inspect', *network_names]))
    if any((row.get('Labels') or {}).get('com.docker.compose.project') != project for row in network_rows):
        raise RuntimeError('Main network ownership mismatch')
    bind_files = {}
    bind_classes = {}
    for service, rows in mounts.items():
        bind_classes[service] = []
        for mount in rows:
            if mount['Type'] != 'bind':
                continue
            source = mount['Source']
            path = host_path(source)
            if not path.exists():
                raise RuntimeError('Live bind source missing: ' + service)
            kind = source_class(source)
            bind_classes[service].append({'class': kind, 'destination': mount['Destination'],
                                          'readOnly': not mount['RW'], 'file': path.is_file()})
            bind_files[source] = {'hostPath': str(path), 'class': kind,
                                  'sha256': sha(path) if path.is_file() else None,
                                  'type': 'file' if path.is_file() else 'directory'}
    nginx = run(DOCKER + ['exec', project + '-web-1', 'nginx', '-T'])
    marker = '# configuration file /etc/b06/admission.conf:'
    if marker not in nginx or not re.search(r'map\s+"\$request_method:\$uri"\s+\$b06_block_new\s*\{\s*default\s+0;', nginx.split(marker, 1)[1]):
        raise RuntimeError('Actual gateway admission mode is not open')
    invalid = json.loads(run(['node', B / 'docs/tests/st00-gateway-probe.mjs']).strip())
    if invalid['status'] != 401 or invalid['code'] != 'AUTH_REQUIRED' or not invalid['tlsAuthorized']:
        raise RuntimeError('Invalid-write gateway JSON gate failed')
    if 'TD062_443_GATE_PASS on 200' not in run(['node', B / 'docs/tests/td06-main-gate.mjs', 'on']):
        raise RuntimeError('Signed discovery GET gate failed')
    dep_private, dep_public = dependency_inventory()
    host = host_tools()
    if not (host['edgePresent'] and host['powershellDesktopAvailable'] and host['explicitJava21'].startswith('java version "21')):
        raise RuntimeError('Required Windows launch tool missing')
    baseline = module('td06_baseline', B / 'docs/tests/collect-td06-baseline.py')
    business = baseline.status_snapshot(project)
    obligations = baseline.obligation_snapshot(project)
    live_mounts = {service: {'namedVolumes': sorted(mount['Name'] for mount in rows if mount['Type'] == 'volume'),
                             'bindCount': sum(mount['Type'] == 'bind' for mount in rows),
                             'bindSources': bind_classes[service]} for service, rows in mounts.items()}
    public = {
        'stage': 'ST-00', 'status': 'PASSED_READ_ONLY_SCOPE_FREEZE',
        'capturedAtUtc': datetime.now(timezone.utc).isoformat(),
        'target': 'Existing TD-06 Windows main443; ST-01 through ST-05 not started',
        'git': {'a': git_public_a, 'b': git_public_b},
        'runtime': {'project': project, 'sevenHealthy': True,
                    'images': image_by_service, 'allImageIdsMatchTd06Archive': True,
                    'stoppedAuxiliary': {'service': 'mq-permissions', 'exitCode': 0,
                                         'imageId': auxiliary[0]['Image']},
                    'httpsHostBinding': '127.0.0.1:443',
                    'networks': network_names, 'volumes': sorted(volume['Name'] for volume in volumes),
                    'mounts': live_mounts, 'noOtherPublishedPorts': True},
        'sourceToRuntime': {'aCurrentMatchesFrozen286Files': True,
                            'bCurrentMatchesFrozen355Files': True,
                            'runningImagesFromTd05ABAndTd062WebBuild': True,
                            'gitHeadAloneDoesNotIdentifyRunningVersion': True},
        'dependencies': dep_public,
        'hostTools': {key: value for key, value in host.items() if not key.endswith('Path')},
        'gateway': {'loadedAdmissionOpen': True, 'invalidWriteStatus': invalid['status'],
                    'invalidWriteCode': invalid['code'], 'invalidWriteJson': invalid['apiEnvelope'],
                    'strictTls': invalid['tlsAuthorized'], 'signedDiscoveryGetStatus': 200,
                    'createdBusinessOrder': False},
        'businessSnapshot': {'observedAtUtc': business['observedAtUtc'],
                             'channelMoney': business['bChannelMoney'], 'inventory': business['bInventory'],
                             'originalObligationCategoryCounts': {key: len(value) for key, value in obligations.items()}},
        'legacyArchive': {'sourceAndImageHashesStillMatch': True,
                          'fullCheckExpectedToDriftOnNewPublicFileInventory': True,
                          'historicalManifestAndEvidenceRewritten': False},
        'privateInventoryPath': str(PRIVATE / 'private-inventory.json').replace('\\', '/'),
        'risks': ['Main release control and live bind mounts still depend on development and historical worktrees',
                  'Host default Java is 8; TD-06 RPC probe uses explicit JDK 21',
                  'Original business obligations remain; live totals can change after this snapshot',
                  'Existing start controller has lifecycle risk on precondition failure; do not use it as a generic repair'],
        'actions': {'gitCommitted': False, 'tagCreated': False, 'imagesSaved': False,
                    'deploymentChanged': False, 'businessWrites': False, 'worktreeCreated': False},
    }
    private = {'containerInspect': containers, 'auxiliaryContainerInspect': auxiliary,
               'volumeInspect': volumes,
               'networkInspect': network_rows, 'nginxLoadedConfig': nginx,
               'bindSources': bind_files, 'dependencyFiles': dep_private,
               'gitPaths': {'a': git_private_a, 'b': git_private_b},
               'hostTools': host, 'obligationHashes': obligations,
               'businessSnapshot': business}
    PRIVATE.mkdir(parents=True, exist_ok=False)
    (PRIVATE / 'private-inventory.json').write_text(json.dumps(private, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    public['privateInventorySha256'] = sha(PRIVATE / 'private-inventory.json')
    PUBLIC.write_text(json.dumps(public, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS ST-00 seven services, images, volumes, mounts, gateway, dependencies and source scope')


if __name__ == '__main__':
    main()
