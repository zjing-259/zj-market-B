"""Read-only structural checks for the ST-04 stable/UX Docker separation."""
from pathlib import Path
import argparse
import json
import re
import subprocess

STABLE = 'zj-market-b06'
UX = 'zj-market-ux'
SERVICES = ('mysql', 'redis', 'namesrv', 'broker', 'marketing-a', 'market-b', 'web')


def docker(*args):
    result = subprocess.run(['docker', '--context', 'desktop-linux', *args],
                            capture_output=True, text=True, check=True)
    return result.stdout


def inspect(project):
    return {service: json.loads(docker('inspect', f'{project}-{service}-1'))[0]
            for service in SERVICES}


def host_path(value):
    # Docker Desktop reports some Windows bind sources as Linux host mounts.
    match = re.fullmatch(r'/run/desktop/mnt/host/([a-zA-Z])/(.*)', value)
    if match:
        value = match.group(1).upper() + ':/' + match.group(2)
    return Path(value).resolve()


def main(ux_root: Path, stable_root: Path):
    ux_root = ux_root.resolve(strict=True)
    stable_root = stable_root.resolve(strict=True)
    if ux_root.name != 'zj-market-ux' or stable_root.name != 'zj-market-stable':
        raise RuntimeError('Unexpected deployment roots')
    stacks = {STABLE: inspect(STABLE), UX: inspect(UX)}
    report = {'status': 'PASS', 'checks': [], 'containerIds': {}, 'imageIds': {}}

    for project, services in stacks.items():
        root = stable_root if project == STABLE else ux_root
        other = ux_root if project == STABLE else stable_root
        report['containerIds'][project] = {}
        report['imageIds'][project] = {}
        for service, item in services.items():
            assert item['Config']['Labels']['com.docker.compose.project'] == project
            assert item['State']['Running'] and item['State']['Health']['Status'] == 'healthy'
            report['containerIds'][project][service] = item['Id'][:12]
            report['imageIds'][project][service] = item['Image']
            for mount in item['Mounts']:
                if mount['Type'] == 'bind':
                    source = host_path(mount['Source'])
                    assert source.is_relative_to(root), (project, service, source)
                    assert not source.is_relative_to(other)
                elif mount['Type'] == 'volume':
                    assert mount['Name'].startswith(project + '_'), mount['Name']
                else:
                    raise RuntimeError(f'Unexpected mount type: {mount["Type"]}')
        report['checks'].append(project + ': seven healthy services, all binds and volumes owned')

    network = {}
    volumes = {}
    for project, services in stacks.items():
        network[project] = set()
        volumes[project] = set()
        for item in services.values():
            network[project].update(v['NetworkID'] for v in item['NetworkSettings']['Networks'].values())
            volumes[project].update(m['Name'] for m in item['Mounts'] if m['Type'] == 'volume')
    assert not network[STABLE] & network[UX]
    assert not volumes[STABLE] & volumes[UX]
    assert len(network[UX]) == 5 and len(volumes[UX]) == 5
    report['checks'].append('distinct five-network and five-volume identities')

    for project, port in ((STABLE, 443), (UX, 8446)):
        bindings = stacks[project]['web']['NetworkSettings']['Ports']['8443/tcp']
        assert len(bindings) == 1 and bindings[0]['HostIp'] == '127.0.0.1'
        assert int(bindings[0]['HostPort']) == port
    assert stacks[STABLE]['marketing-a']['Image'] == stacks[UX]['marketing-a']['Image']
    assert stacks[STABLE]['market-b']['Image'] == stacks[UX]['market-b']['Image']
    assert stacks[STABLE]['web']['Image'] != stacks[UX]['web']['Image']
    report['checks'].append('different loopback ports and UX-only web image; separate A/B containers')

    b = (ux_root / 'deploy/b06/config/b.properties').read_text(encoding='utf-8')
    broker = (ux_root / 'deploy/b06/config/broker.conf').read_text(encoding='utf-8')
    opener = (ux_root / 'scripts/open-st04-ux.ps1').read_text(encoding='utf-8')
    assert 'b.identity.origin=https://zj-market-ux.test:8446' in b
    assert 'b.infrastructure.rpc.url=tri://marketing-a:50051' in b
    assert 'b.infrastructure.mq.nameserver=namesrv:9876' in b
    assert 'brokerIP1=broker' in broker and 'namesrvAddr=namesrv:9876' in broker
    assert '.local/st04/browser-profile' in opener and 'zj-market-ux.test' in opener
    report['checks'].append('UX origin, internal RPC/MQ and separate browser profile configured')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ux-root', type=Path, default=Path('D:/Java/zj-market-ux'))
    parser.add_argument('--stable-root', type=Path, default=Path('D:/Java/zj-market-stable'))
    args = parser.parse_args()
    main(args.ux_root, args.stable_root)
