"""UX05 successor release. Preserve frozen TD06 artifacts and every existing live volume.

Backup is an offline recovery artifact only. Rollback always uses current data and
compatible fixed images; this tool contains no volume/data restore operation.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, os, re, shutil, subprocess

ROOT = Path(__file__).resolve().parents[1]
STABLE = Path('D:/Java/zj-market-stable')
OLD = 'td06-stable-20261016-01'
NEW = 'ux05-stable-20261019-01'
WEB = 'sha256:fdd4072544a5290a3d51f58b8d1cbd83cac02bcb6eb2a20abaf9f3b3a9bbc145'
PROJECT = 'zj-market-b06'
SERVICES = ['mysql', 'redis', 'namesrv', 'broker', 'marketing-a', 'market-b', 'web']

def sha(file):
    h = hashlib.sha256()
    with Path(file).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest().upper()

def load(file):
    return json.loads(Path(file).read_text(encoding='utf-8-sig'))

def write(file, data):
    file = Path(file)
    file.parent.mkdir(parents=True, exist_ok=True)
    temp = file.with_suffix(file.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    os.replace(temp, file)

def run(label, args, timeout=600):
    r = subprocess.run([str(x) for x in args], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    if r.returncode:
        raise RuntimeError(label + ' failed; private output withheld')
    return r.stdout

def private_acl(directory):
    account = run('account', ['whoami']).strip()
    run('private inheritance', ['icacls', directory, '/inheritance:r'])
    run('private permissions', ['icacls', directory, '/grant:r', account+':(OI)(CI)F', 'SYSTEM:(OI)(CI)F', 'Administrators:(OI)(CI)F'])

def controller(release):
    spec = importlib.util.spec_from_file_location('release_' + release.replace('-', '_'), STABLE/'releases'/release/'controller.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Controller(STABLE)

def snapshot(c):
    statements = {
        'moneyStock': "SELECT 'paid',COALESCE(SUM(amount),0) FROM zj_market_b06.b_sim_payment WHERE gate='PAID'; SELECT 'refunded',COALESCE(SUM(refunded_amount),0) FROM zj_market_b06.b_sim_refund; SELECT 'available',COALESCE(SUM(available),0) FROM zj_market_b06.b_inventory_account; SELECT 'reserved',COALESCE(SUM(reserved),0) FROM zj_market_b06.b_inventory_account; SELECT 'sold',COALESCE(SUM(sold),0) FROM zj_market_b06.b_inventory_account;",
        'obligations': "SELECT 'aReconciling',COUNT(*) FROM group_buy_market_b06.ab_team WHERE team_status='RECONCILING'; SELECT 'aPaid',COUNT(*) FROM group_buy_market_b06.ab_trade_order WHERE order_status='PAID'; SELECT 'bTradeWork',COUNT(*) FROM zj_market_b06.b_trade_work WHERE state NOT IN ('DONE','DEAD'); SELECT 'bTradeInbox',COUNT(*) FROM zj_market_b06.b_trade_inbox WHERE state NOT IN ('DONE','DEAD'); SELECT 'bTradeOutbox',COUNT(*) FROM zj_market_b06.b_trade_outbox WHERE state NOT IN ('DONE','DEAD'); SELECT 'bRefundTask',COUNT(*) FROM zj_market_b06.b_refund_task WHERE state NOT IN ('DONE','DEAD');",
        'originalOrders': "SELECT order_id,business_status,goods_id,quantity FROM zj_market_b06.b_market_order ORDER BY order_id;",
        'ledgerCounts': "SELECT kind,COUNT(*),SUM(delta_available) FROM zj_market_b06.b_inventory_ledger GROUP BY kind ORDER BY kind;",
    }
    return {name: c.sql(sql).splitlines() for name, sql in statements.items()}

def freeze():
    old = controller(OLD)
    old.ready()
    release_dir, private_dir = STABLE/'releases'/NEW, STABLE/'private'/NEW
    if release_dir.exists() or private_dir.exists():
        controller(NEW).check_bundle()
        print('UX05_FREEZE_ALREADY_VERIFIED', flush=True)
        return
    release_dir.mkdir(parents=True)
    private_dir.mkdir(parents=True)
    private_acl(private_dir)
    manifest = load(STABLE/'private/files-manifest.json')
    for item in manifest['files']:
        relative = Path(item['relativePath'])
        if relative.is_absolute() or '..' in relative.parts:
            raise RuntimeError('Unsafe private manifest path')
        dest = private_dir/relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(STABLE/'private'/relative, dest)
    files = {
        'files/009-admission-open.conf': (ROOT/'deploy/b06/config/admission-open.conf').read_text(),
        'files/033-admission-maintenance.conf': (ROOT/'deploy/b06/config/admission-maintenance.conf').read_text(),
        'files/037-ux05-nginx.conf': (ROOT/'deploy/b06/nginx.conf').read_text().replace('server_name zj-market-ux.test;', 'server_name zj-market.test;'),
    }
    cap_file = private_dir/'files/004-capabilities-open.properties'
    cap = cap_file.read_text()
    if re.search(r'^b.team-discovery.enabled=', cap, re.M):
        cap = re.sub(r'^b.team-discovery.enabled=.*$', 'b.team-discovery.enabled=true', cap, flags=re.M)
    else:
        cap += '\nb.team-discovery.enabled=true\n'
    files['files/004-capabilities-open.properties'] = cap
    for relative, content in files.items():
        (private_dir/relative).write_text(content, encoding='utf-8')
    old_items = {item['relativePath']: item for item in manifest['files']}
    for relative in files:
        file = private_dir/relative
        old_items[relative] = {'relativePath': relative, 'sha256': sha(file), 'bytes': file.stat().st_size}
    manifest['files'] = list(old_items.values())
    write(private_dir/'files-manifest.json', manifest)
    release = load(old.release_path)
    release.update(release=NEW, previousRelease=OLD, sourceCommitUX=run('UX commit', ['git', '-C', ROOT, 'rev-parse', 'HEAD']).strip(),
                   privateManifestSha256=sha(private_dir/'files-manifest.json'))
    release['images']['web'] = WEB
    for mode in ['on', 'maintenance']:
        template = load(old.release_dir/f'compose-{mode}.template.json')
        template['services']['web']['image'] = WEB
        template['services']['web']['volumes'].append({'type': 'bind', 'source': '@private/files/037-ux05-nginx.conf', 'target': '/etc/nginx/nginx.conf', 'read_only': True, 'bind': {'create_host_path': False}})
        dest = release_dir/f'compose-{mode}.template.json'
        write(dest, template)
        release['templates'][mode] = {'file': str(dest.relative_to(STABLE)).replace('\\', '/'), 'sha256': sha(dest)}
    for name in release['tools']:
        text = (old.release_dir/name).read_text(encoding='utf-8-sig').replace(OLD, NEW)
        if name == 'controller.py':
            text = text.replace("self.private_dir = self.root / 'private'", "self.private_dir = self.root / 'private' / RELEASE")
        if name == 'open-stable.ps1':
            text = text.replace("'private\\files-manifest.json'", "'private\\"+NEW+"\\files-manifest.json'").replace("(Join-Path $Root 'private')", "(Join-Path $Root 'private\\"+NEW+"')")
        if name == 'stable-probe.mjs':
            text += "\nconst mode = await request('/system/status'); if(mode.status !== 200 || mode.payload.data?.mode !== 'NORMAL') throw Error('UX05 public gateway status mismatch');\n"
        (release_dir/name).write_text(text, encoding='utf-8')
    release['tools'] = {name: sha(release_dir/name) for name in release['tools']}
    write(release_dir/'release.json', release)
    candidate = controller(NEW)
    candidate.check_bundle()
    candidate.docker_inventory()
    for mode in ['on', 'maintenance']:
        rendered = STABLE/'state'/f'ux05-candidate-{mode}.json'
        write(rendered, candidate.rendered(mode))
        candidate.run('candidate Compose validation', candidate.docker+['compose', '-p', PROJECT, '-f', str(rendered), 'config', '-q'])
    archive = ROOT/'.local/ux04/images/web-ux04-20261019-01.tar'
    if sha(archive) != 'F5B06A0AC7A9557BBA88C48ED7612243DB95F5BD7C9BB4FC3205214C61456622':
        raise RuntimeError('Candidate image archive drift')
    shutil.copy2(archive, STABLE/'images/web-ux05-20261019-01.tar')
    write(ROOT/'.local/ux05/release-freeze.json', {'status': 'FROZEN', 'release': NEW, 'releaseSha256': sha(candidate.release_path), 'images': release['images'], 'webArchiveSha256': sha(archive), 'schemaFingerprint': release['schemaFingerprint'], 'flywayHistorySha256': release['flywayHistorySha256'], 'tools': release['tools'], 'oldFrozenReleaseUnchanged': True})
    print('UX05_RELEASE_FROZEN original-TD06-files-retained', flush=True)

def raw(label, args, file):
    with file.open('wb') as output:
        result = subprocess.run([str(x) for x in args], stdout=output, stderr=subprocess.DEVNULL, timeout=1200)
    if result.returncode or file.stat().st_size == 0:
        raise RuntimeError(label+' failed')

def journal(backup, phase):
    write(backup/'journal.json', {'phase': phase, 'atUtc': datetime.now(timezone.utc).isoformat()})
    print('UX05_PHASE '+phase, flush=True)

def launcher(release):
    file = STABLE/'scripts/stable.ps1'
    text = file.read_text(encoding='utf-8-sig')
    text = text.replace(OLD, release) if release == NEW else text.replace(NEW, release)
    temp = file.with_suffix('.ps1.tmp')
    temp.write_text(text, encoding='utf-8')
    os.replace(temp, file)

def upgrade(batch):
    old, new = controller(OLD), controller(NEW)
    old.ready(); new.check_bundle(); new.docker_inventory()
    backup = STABLE/'backups'/batch
    if backup.exists():
        raise RuntimeError('Existing upgrade journal; inspect before resume/rollback')
    backup.mkdir(parents=True); private_acl(backup)
    for name, source in [('old-adoption.json', STABLE/'state/adoption.json'), ('old-launcher.ps1', STABLE/'scripts/stable.ps1')]:
        shutil.copy2(source, backup/name)
    shutil.copytree(old.release_dir, backup/'old-release')
    private_copy = backup/'old-private'
    private_copy.mkdir()
    for item in old.private_manifest['files']:
        source = old.private_dir/item['relativePath']; dest = private_copy/item['relativePath']
        dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, dest)
    shutil.copy2(old.private_dir/'files-manifest.json', private_copy/'files-manifest.json')
    journal(backup, 'SOURCE_READY')
    with old.lock():
        old.armed(); old.preflight()
        try:
            old.compose('maintenance', 'up', '-d', '--pull', 'never', '--no-build', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '90', 'web')
            if old.gateway_mode() != 'MAINTENANCE':
                raise RuntimeError('Main maintenance gate not confirmed')
            journal(backup, 'GATE_CLOSED')
            old.compose('maintenance', 'stop', 'web', 'market-b', 'marketing-a', 'broker', 'namesrv', 'redis')
            if any(v['State']['Running'] for k,v in old.inspect().items() if k != 'mysql'):
                raise RuntimeError('Main writer still active')
            write(backup/'baseline.json', snapshot(old))
            raw('logical dump', old.docker+['exec', PROJECT+'-mysql-1', 'sh', '-c', 'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysqldump -uroot --single-transaction --routines --triggers --events --databases group_buy_market_b06 zj_market_b06'], backup/'business.sql')
            old.sql('SET GLOBAL innodb_fast_shutdown=0;')
            old.compose('maintenance', 'stop', 'mysql')
            if any(v['State']['Running'] for v in old.inspect().values()):
                raise RuntimeError('Main stack not cold')
            journal(backup, 'COLD_POINT')
            for volume in old.release['volumes']:
                raw('cold volume', old.docker+['run', '--rm', '--network', 'none', '--read-only', '--cap-drop', 'ALL', '--cap-add', 'DAC_OVERRIDE', '--mount', 'type=volume,src='+volume+',dst=/volume,readonly', '--entrypoint', 'tar', old.release['images']['redis'], '--numeric-owner', '-cpf', '-', '-C', '/volume', '.'], backup/(volume+'.tar'))
            files = {str(p.relative_to(backup)).replace('\\','/'): {'sha256': sha(p), 'bytes': p.stat().st_size} for p in backup.rglob('*') if p.is_file() and p.name != 'journal.json'}
            write(backup/'manifest.json', {'status': 'COMPLETE', 'project': PROJECT, 'batch': batch, 'files': files, 'volumes': old.release['volumes'], 'restoreOverLiveVolumes': False})
            if any(sha(backup/name) != v['sha256'] for name,v in files.items()):
                raise RuntimeError('Cold backup hash mismatch')
            write(backup/'COMPLETE.json', {'manifestSha256': sha(backup/'manifest.json')})
            journal(backup, 'BACKUP_COMPLETE')
            new.preflight()
            # inspect() enforces the new web ID even while stopped. Replace only
            # the stopped web container before the normal guarded start path.
            new.compose('maintenance', 'create', '--no-build', '--pull', 'never', 'web')
            write(STABLE/'state/adoption.json', {'release': NEW, 'project': PROJECT, 'releaseSha256': sha(new.release_path), 'backupBatch': batch, 'backupManifestSha256': sha(backup/'manifest.json')})
            journal(backup, 'SUCCESSOR_ARMED')
        except Exception:
            journal(backup, 'RECOVERY_REQUIRED_GATE_CLOSED')
            raise
    finish(new, backup, batch)

def finish(new, backup, batch):
    new.start()
    after = snapshot(new)
    before = load(backup/'baseline.json')
    if before != after:
        new.close_after_failure(); journal(backup, 'FACTS_DIFFER_GATE_CLOSED')
        raise RuntimeError('Pre-existing facts differ after startup; inspect original obligations')
    launcher(NEW)
    journal(backup, 'UPGRADED_READY')
    write(ROOT/'.local/ux05/main-upgrade.json', {'status': 'PASS', 'release': NEW, 'backupBatch': batch, 'backupManifestSha256': sha(backup/'manifest.json'), 'preExistingFactsPreserved': True, 'before': before, 'after': after, 'ready': new.ready(), 'rollback': 'compatible images with current data; never restore backup over live volumes'})
    print('UX05_MAIN_UPGRADED original-money-stock-orders-obligations-preserved', flush=True)

def resume(batch):
    """Only continue a verified cold backup. No writes if any service is running."""
    backup = STABLE/'backups'/batch
    if load(backup/'COMPLETE.json')['manifestSha256'] != sha(backup/'manifest.json'):
        raise RuntimeError('Cold backup manifest identity mismatch')
    for name, item in load(backup/'manifest.json')['files'].items():
        file = (backup/name).resolve()
        if not file.is_relative_to(backup.resolve()) or sha(file) != item['sha256']:
            raise RuntimeError('Cold backup file mismatch')
    old, new = controller(OLD), controller(NEW)
    new.check_bundle();new.docker_inventory()
    rows = json.loads(new.run('cold container inspection', new.docker+['inspect', *[PROJECT+'-'+name+'-1' for name in SERVICES]]))
    for row in rows:
        name = row['Config']['Labels'].get('com.docker.compose.service')
        if row['Config']['Labels'].get('com.docker.compose.project') != PROJECT or name not in SERVICES or row['State']['Running']:
            raise RuntimeError('Resume requires owned, completely stopped main stack')
        role = new.release['serviceImageRoles'][name]
        if row['Image'] not in [old.release['images'][role], new.release['images'][role]]:
            raise RuntimeError('Unexpected image at cold resume')
    with old.lock():
        new.preflight()
        # Compose 2.28 create recursively creates dependencies, but starts none.
        new.compose('maintenance', 'create', '--no-build', '--pull', 'never', 'web')
        if any(row['State']['Running'] for row in new.inspect().values()):
            raise RuntimeError('Unexpected running service during cold resume')
        write(STABLE/'state/adoption.json', {'release': NEW, 'project': PROJECT, 'releaseSha256': sha(new.release_path), 'backupBatch': batch, 'backupManifestSha256': sha(backup/'manifest.json')})
        journal(backup, 'SUCCESSOR_ARMED')
    finish(new, backup, batch)

def rollback(batch):
    backup = STABLE/'backups'/batch
    if not (backup/'COMPLETE.json').is_file() or load(backup/'COMPLETE.json')['manifestSha256'] != sha(backup/'manifest.json'):
        raise RuntimeError('Completed backup identity required')
    new, old = controller(NEW), controller(OLD)
    # Used after a completed upgrade. Failed/partial startup remains closed and
    # requires diagnosis; never force an unknown running service state.
    new.stop()
    old.preflight()
    old.compose('maintenance', 'create', '--no-build', '--pull', 'never', 'web')
    write(STABLE/'state/adoption.json', load(backup/'old-adoption.json'))
    old.start(); launcher(OLD)
    journal(backup, 'ROLLED_BACK_CURRENT_DATA')
    print('UX05_ROLLBACK_READY current-data-retained', flush=True)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['freeze', 'upgrade', 'resume', 'rollback', 'ready'])
    p.add_argument('--batch', default='ux05-main-20261019-01')
    a = p.parse_args()
    if ROOT.name != 'zj-market-ux' or not re.fullmatch(r'ux05-main-[0-9]{8}-[0-9]{2}', a.batch):
        raise RuntimeError('Explicit owned root/batch required')
    if a.action == 'freeze': freeze()
    elif a.action == 'ready': print(json.dumps(controller(NEW).ready()))
    else: globals()[a.action](a.batch)

if __name__ == '__main__':
    main()
