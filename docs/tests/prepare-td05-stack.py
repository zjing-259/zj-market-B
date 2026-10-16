"""Restore a sealed B-06 snapshot into TD-05-owned volumes and run fixed A/B/web images.

This only creates resources named by --run-name. It never stops or reconfigures B-06.
Private copied material and raw logs stay in ignored target/team-discovery.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, re, shutil, subprocess, time

B = Path(__file__).resolve().parents[2]
A = Path('D:/Java/group-buy-market')
SOURCE = Path('D:/Java/zj-market-b-06/.local/b06/backups/b066-final-20261012-01')
DOCKER = ['docker', '--context', 'desktop-linux']
VOLUMES = ('mysql-data', 'redis-data', 'broker-store', 'broker-logs', 'namesrv-logs')

def run(args, *, input=None, timeout=600):
    result = subprocess.run([str(x) for x in args], input=input, capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=timeout)
    if result.returncode:
        raise RuntimeError('Failed command: ' + ' '.join(str(x) for x in args[:5]))
    return result.stdout

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def replace_property(path, key, value):
    lines = path.read_text(encoding='utf-8').splitlines()
    lines = [line for line in lines if not line.startswith(key + '=')]
    lines.append(key + '=' + value)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

def configure_a_logging(work, config):
    target = work / 'private/config/logback-td05.xml'
    target.write_text('''<configuration><appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender"><encoder><pattern>%d %-5level %logger{32} - %msg%n</pattern></encoder></appender><root level="INFO"><appender-ref ref="STDOUT"/></root></configuration>\n''', encoding='utf-8')
    service = config['services']['marketing-a']
    if not any(m.get('target') == '/etc/b06/logback-td05.xml' for m in service['volumes']):
        service['volumes'].append({'type':'bind','source':str(target),'target':'/etc/b06/logback-td05.xml','read_only':True})
    option = '--logging.config=file:/etc/b06/logback-td05.xml'
    if option not in service['command']: service['command'].append(option)

def main(name):
    if not re.fullmatch(r'td05_[0-9]{8}_[0-9]{2}', name):
        raise ValueError('Use a new td05_YYYYMMDD_NN name')
    work = B / 'target/team-discovery' / name
    if (work / 'prepare-report.json').exists(): raise RuntimeError('TD05 project already prepared')
    work.mkdir(parents=True, exist_ok=True)
    project = 'zj-market-' + name.replace('_', '-')
    report = {'stage': 'TD-05', 'runName': name, 'project': project, 'status': 'RUNNING', 'checks': []}
    def record(label):
        report['checks'].append(label)
        save(work / 'prepare-report.json', report)
        print('PASS ' + label, flush=True)
    save(work / 'prepare-report.json', report)
    try:
        spec = importlib.util.spec_from_file_location('backup', Path('D:/Java/zj-market-b-06/scripts/b06-backup.py'))
        backup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backup)
        manifest = backup.validate_manifest(SOURCE)
        record('sealed-source-backup-hashes')
        protect_spec = importlib.util.spec_from_file_location('protect', B / 'scripts/prepare-b06-secrets.py')
        protect = importlib.util.module_from_spec(protect_spec)
        protect_spec.loader.exec_module(protect)
        protect.protect_windows(work)
        shutil.copytree(SOURCE / 'bundle', work / 'private')
        replace_property(work / 'private/config/b.properties', 'b.identity.origin', 'https://zj-market.test:8445')
        replace_property(work / 'private/config/b.properties', 'b.team-discovery.enabled', 'false')
        for key in ('b.payment.checkout-enabled','b.reconciliation.enabled','b.refund.enabled'):
            replace_property(work / 'private/control/capabilities.properties', key, 'true')
        record('private-bundle-copied-with-td05-origin-and-feature-flag')
        release = json.loads((work / 'release-manifest.json').read_text(encoding='utf-8'))
        if release['status'] != 'BUILT_LOCAL_ONLY' or set(release['images']) != {'a','b','web'}:
            raise RuntimeError('TD05 images not built')
        report['images'] = release['images']
        save(work / 'prepare-report.json', report)
        config = json.loads((SOURCE / 'compose-snapshot.json').read_text(encoding='utf-8'))
        config['name'] = project
        for offset, network in enumerate(config['networks'], 40):
            config['networks'][network]['name'] = project + '_' + network
            config['networks'][network]['ipam'] = {'config':[{'subnet':f'10.250.{offset}.0/24'}]}
        for name_, item in config['secrets'].items():
            item['name'] = project + '_' + name_
            item['file'] = str(work / 'private' / Path(item['file']).relative_to(SOURCE / 'bundle'))
        for service in config['services'].values():
            service.pop('container_name', None)
            service.get('labels', {}).pop('com.docker.compose.project', None)
            for mount in service.get('volumes', []):
                if mount['type'] == 'bind':
                    mount['source'] = str(work / 'private' / Path(mount['source']).relative_to(SOURCE / 'bundle'))
        for volume in VOLUMES:
            config['volumes'][volume] = {'external': True, 'name': project + '_' + volume}
        config['services']['marketing-a']['image'] = release['images']['a']['id']
        configure_a_logging(work, config)
        config['services']['market-b']['image'] = release['images']['b']['id']
        config['services']['web']['image'] = release['images']['web']['id']
        config['services']['web']['ports'][0]['published'] = '8445'
        for mount in config['services']['web']['volumes']:
            if mount['target'] == '/etc/b06/admission.conf':
                mount['source'] = str(work / 'private/config/admission-open.conf')
        compose = work / 'compose.json'
        save(compose, config)
        run(DOCKER + ['compose','-p',project,'-f',compose,'config','--quiet'])
        record('isolated-compose-validated')
        all_existing = run(DOCKER + ['ps','-a','--filter','label=com.docker.compose.project='+project,'--format','{{.ID}}']).strip()
        if all_existing: raise RuntimeError('TD04 project already has containers')
        image = json.loads((B / 'deploy/b06/images.lock.json').read_text(encoding='utf-8'))['redis']
        for volume in VOLUMES:
            target = project + '_' + volume
            if run(DOCKER + ['volume','ls','--filter','name=^'+target+'$','--format','{{.Name}}']).strip():
                raise RuntimeError('TD04 volume already exists: ' + target)
            run(DOCKER + ['volume','create','--label','td05.owner='+name,'--label','com.docker.compose.project='+project,target])
            run(DOCKER + ['run','--rm','--network','none','--label','td05.owner='+name,
                          '--mount','type=volume,src='+target+',dst=/volume',
                          '--mount','type=bind,src='+str(SOURCE)+',dst=/backup,readonly',
                          '--entrypoint','sh',image,'-c','tar --numeric-owner -xpf /backup/'+volume+'.tar -C /volume'],timeout=1200)
            record('restored-own-volume-'+volume)
        run(DOCKER + ['compose','-p',project,'-f',compose,'up','-d','--wait','--wait-timeout','180',
                      'mysql','redis','namesrv','broker'],timeout=300)
        record('isolated-middleware-healthy')
        migrate = "USE group_buy_market_b06;\n" + (A / 'docs/dev-ops/mysql/sql/migrations/20261014-team-discovery.sql').read_text(encoding='utf-8')
        run(DOCKER + ['exec','-i',project+'-mysql-1','sh','-c',
                      'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw'],input=migrate,timeout=180)
        record('td05-a-indexes-applied-only-to-clone')
        run(DOCKER + ['compose','-p',project,'-f',compose,'up','-d','--wait','--wait-timeout','180',
                      'marketing-a'],timeout=300)
        record('new-a-image-healthy-before-b')
        run(DOCKER + ['compose','-p',project,'-f',compose,'up','-d','--wait','--wait-timeout','180',
                      'market-b','web'],timeout=300)
        record('new-a-b-web-images-healthy-in-isolated-project')
        report['status'] = 'READY'
        save(work / 'prepare-report.json', report)
    except Exception as exc:
        report['status'] = 'FAILED'
        report['error'] = type(exc).__name__ + ': ' + str(exc)
        save(work / 'prepare-report.json', report)
        raise

def resume(name):
    if not re.fullmatch(r'td05_[0-9]{8}_[0-9]{2}', name): raise ValueError('Invalid TD05 batch')
    work = B / 'target/team-discovery' / name
    report = json.loads((work / 'prepare-report.json').read_text(encoding='utf-8'))
    project = report['project']
    config = json.loads((work / 'compose.json').read_text(encoding='utf-8'))
    if config['name'] != project or not project.startswith('zj-market-td05-'):
        raise RuntimeError('Unsafe project identity')
    query = "SELECT COUNT(DISTINCT INDEX_NAME) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='group_buy_market_b06' AND INDEX_NAME IN ('idx_ab_team_discovery','idx_ab_order_discovery_owner');"
    mysql = DOCKER + ['exec','-i',project+'-mysql-1','sh','-c',
                      'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --raw --skip-column-names']
    count = int(run(mysql,input=query).strip())
    if count == 0:
        migration = "USE group_buy_market_b06;\n" + (A / 'docs/dev-ops/mysql/sql/migrations/20261014-team-discovery.sql').read_text(encoding='utf-8')
        run(mysql,input=migration,timeout=180)
    elif count != 2:
        raise RuntimeError('Partial A discovery migration')
    report['checks'].append('td05-a-indexes-applied-only-to-clone')
    configure_a_logging(work, config)
    save(work / 'compose.json', config)
    run(DOCKER + ['compose','-p',project,'-f',work / 'compose.json','up','-d','--wait','--wait-timeout','180',
                  'marketing-a'],timeout=300)
    report['checks'].append('new-a-image-healthy-before-b')
    run(DOCKER + ['compose','-p',project,'-f',work / 'compose.json','up','-d','--wait','--wait-timeout','180',
                  'market-b','web'],timeout=300)
    report['status'] = 'READY'
    report.pop('error',None)
    report['checks'].append('new-a-b-web-images-healthy-in-isolated-project')
    save(work / 'prepare-report.json', report)
    print('PASS new-a-b-web-images-healthy-in-isolated-project', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-name', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    (resume if args.resume else main)(args.run_name)

