"""Collect actual B-05.2 evidence without rerunning or rewriting historical batches.

Local evidence paths are required. This collector does not execute business operations.
"""
import argparse
import hashlib
import io
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--run-name', required=True)
    p.add_argument('--sql-batch', required=True)
    p.add_argument('--completed-batch', required=True)
    p.add_argument('--partial-batch', required=True)
    p.add_argument('--regression-prefix', required=True)
    p.add_argument('--ordinary-batch', default='b052-ordinary-start')
    p.add_argument('--external-a-snapshot', help='Optional explicit fingerprint snapshot for concurrent A config edits; tested A JAR must remain identical')
    p.add_argument('--protected-after', required=True, help='read-only SQL snapshot in the same format as the SQL batch')
    a = p.parse_args()
    for value in [a.run_name, a.sql_batch, a.completed_batch, a.partial_batch, a.regression_prefix, a.ordinary_batch]:
        if not re.fullmatch(r'[A-Za-z0-9-]+', value):
            p.error('Use simple fresh batch names')
    work = ROOT / 'target/reconciliation' / a.run_name
    work.mkdir(parents=True, exist_ok=False)
    report = {'stage': 'B-05.2', 'status': 'RUNNING', 'checks': [], 'evidence': {},
              'scope': 'simulated funds; actual MySQL/row locks/channel/two JVMs and actual A/TLS/signed MQ; refund execution is B-05.3'}

    def check(ok, name):
        report['checks'].append({'name': name, 'passed': bool(ok)})
        if not ok:
            raise AssertionError(name)

    def evidence(path, label, json_report=False):
        raw = path.read_text(encoding='utf-8-sig')
        check(json.loads(raw)['status'] == 'PASSED' if json_report else 'status=PASSED' in raw.splitlines(), label)
        report['evidence'][label] = {'path': str(path), 'sha256': digest(path)}
        return raw

    try:
        git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
        report['branch'], report['head'] = git('branch', '--show-current'), git('rev-parse', 'HEAD')
        check(report['branch'] == 'b-05', 'b-05 worktree')
        report['gitStatus'] = git('status', '--short')
        jar = ROOT / 'zj-market-verification/target/zj-market-verification.jar'
        jar_hash = digest(jar)
        report['verificationJarSha256'] = jar_hash
        sql = ROOT / 'target/reconciliation' / a.sql_batch
        sql_report = json.loads(evidence(sql / 'report.json', 'SQL/channel/JVM batch', True))
        check(sql_report['verificationJarSha256'].lower() == jar_hash, 'SQL same verification package')
        check(sql_report['oldProtectedRowsMissingOrChanged'] == 0, 'SQL batch original protected rows unchanged')
        for schema in ['test', 'development']:
            raw = evidence(sql / f'{schema}-permissions.txt', f'{schema} runtime permissions')
            check('runtimeDDL/history/A/system/grant=DENIED' in raw, f'{schema} prohibited grants denied')
            grants = [line for line in raw.splitlines() if line.startswith('grant=GRANT SELECT, INSERT, UPDATE, DELETE ON')]
            check(len(grants) == 41, f'{schema} exact 41-table DML grants')
        for batch, modes, label in [(a.completed_batch, ['reconciliation-completed'], 'completed competition'),
                                    (a.partial_batch, ['reconciliation', 'reconciliation-recover'], 'partial payment restart')]:
            base = ROOT / 'target/b03-readiness' / batch
            info = json.loads(evidence(base / 'report.json', label, True))
            check(all(info[k] for k in ['environmentRestored', 'ownedPortsReleased', 'defaultJavaUnchanged']), label + ' environment/port/Java restoration')
            provenance = dict(line.split('=', 1) for line in (base / 'provenance.txt').read_text(encoding='utf-8-sig').splitlines() if '=' in line)
            check(provenance['B-verification-jar-sha256'].lower() == jar_hash, label + ' same package')
            check(provenance['A-jar-sha256'].lower() == digest(ROOT.parent / 'group-buy-market/group-buy-market-app/target/group-buy-market-app.jar'), label + ' actual A runtime package unchanged')
            for mode in modes:
                evidence(base / (mode + '.txt'), label + '/' + mode)
        for area, suffix in [('payment-closing', 'closing-regression'), ('settlement', 'settlement-regression'), ('fulfillment', 'fulfillment-regression')]:
            base = ROOT / 'target' / area / (a.regression_prefix + '-' + suffix)
            for mode in ['verify', 'recover']:
                evidence(base / (mode + '.txt'), area + '/' + mode)
        before = json.loads((ROOT / 'target/reconciliation/b052-20261010-01/before.json').read_text(encoding='utf-8'))
        for file, expected in before['oldMigrations'].items():
            check(digest(ROOT / file) == expected, 'historical migration unchanged: ' + Path(file).name)
        check(digest(ROOT.parent / 'group-buy-market/docs/ab-api-contract.md') == before['aContract'], 'A contract unchanged')
        check(not subprocess.check_output(['git', '-C', str(ROOT.parent / 'zj-market-b-04'), 'status', '--porcelain'], text=True).strip(), 'B-04 unchanged')
        a_root = ROOT.parent / 'group-buy-market'
        a_status = subprocess.check_output(['git', '-C', str(a_root), 'status', '--porcelain'], text=True)
        if a.external_a_snapshot:
            state = json.loads((ROOT / a.external_a_snapshot).read_text(encoding='utf-8'))
            allowed = {f'group-buy-market-app/src/main/resources/application-{profile}.yml' for profile in ['dev', 'prod', 'test']}
            check(set(state['files']) == allowed and state['status'] == a_status, 'external A changes limited to explicitly recorded source configs')
            check(all(digest(a_root / file) == value for file, value in state['files'].items()), 'external A config bytes preserved')
            check(state['head'] == subprocess.check_output(['git', '-C', str(a_root), 'rev-parse', 'HEAD'], text=True).strip(), 'A Git baseline unchanged')
            check(state['runtimeJarSha256'] == digest(a_root / 'group-buy-market-app/target/group-buy-market-app.jar'), 'external A edits did not replace tested artifact')
            report['externalAState'] = state
        else:
            check(not a_status.strip(), 'A worktree unchanged')
        boundary = json.loads((ROOT / 'target/reconciliation/b052-main-roadmap-boundary.json').read_text(encoding='utf-8'))
        raw = (ROOT.parent / 'zj-market/docs/development-roadmap.md').read_bytes()
        insertion = (boundary['insertion'] + '\n').encode()
        check(raw.count(insertion) == 1 and hashlib.sha256(raw.replace(insertion, b'')).hexdigest() == boundary['beforeSha256'], 'main roadmap unrelated bytes preserved')
        protected_before = set((sql / 'before-protected.txt').read_text(encoding='utf-8-sig').splitlines())
        protected_after_path = ROOT / a.protected_after
        protected_after = set(protected_after_path.read_text(encoding='utf-8-sig').splitlines())
        report['protectedRowsBefore'] = len(protected_before)
        report['protectedRowsMissingOrChanged'] = len(protected_before - protected_after)
        check(not (protected_before - protected_after), 'original funds/work/HELD/guard/channel retained through regressions')
        report['evidence']['protected-after'] = {'path': str(protected_after_path), 'sha256': digest(protected_after_path)}
        suites = [ET.parse(f).getroot() for f in (ROOT / 'zj-market-app/target/surefire-reports').glob('TEST-*.xml')]
        report['junit'] = {key: sum(int(s.attrib.get(key, 0)) for s in suites) for key in ['tests', 'failures', 'errors', 'skipped']}
        check(report['junit']['tests'] >= 87 and not any(report['junit'][k] for k in ['failures', 'errors', 'skipped']), 'JUnit 87 or more, all passing')
        app_jar = ROOT / 'zj-market-app/target/zj-market-app-exec.jar'
        report['applicationJarSha256'] = digest(app_jar)
        ordinary = json.loads(evidence(ROOT / 'target/reconciliation' / a.ordinary_batch / 'report.json', 'ordinary default startup', True))
        check(ordinary['applicationJarSha256'].lower() == report['applicationJarSha256'], 'ordinary startup same executable package')
        with zipfile.ZipFile(app_jar) as z:
            names = z.namelist()
            check(not any('flyway' in n.lower() or 'verification' in n.lower() for n in names), 'ordinary application excludes migration runner and verification')
            major = int.from_bytes(z.read('BOOT-INF/classes/cn/zj/zjmarket/ZjMarketApplication.class')[6:8], 'big')
            check(major == 65, 'application Java 21 bytecode')
            a_contracts = [n for n in names if re.search(r'/group-buy-market-contract-[^/]+\.jar$', n)]
            check(len(a_contracts) == 1, 'one original A contract dependency')
            with zipfile.ZipFile(io.BytesIO(z.read(a_contracts[0]))) as c:
                check(int.from_bytes(c.read('cn/bugstack/api/v2/TeamService.class')[6:8], 'big') == 52, 'A contract remains Java 8 bytecode')
        props = (ROOT / 'zj-market-app/src/main/resources/application.properties').read_text(encoding='utf-8')
        check('b.reconciliation.enabled=${B_RECONCILIATION_ENABLED:false}' in props, 'new reconciliation admission defaults off')
        check('b.reconciliation.recovery-enabled=${B_RECONCILIATION_RECOVERY_ENABLED:true}' in props, 'existing task recovery defaults on within trade-events capability')
        report['sourceSha256'] = {str(f.relative_to(ROOT)): digest(f) for f in ROOT.rglob('*.java') if 'target' not in f.parts}
        report['status'] = 'PASSED'
    except Exception as e:
        report['status'] = 'FAILED'
        report['error'] = str(e)
        raise
    finally:
        (work / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('B-05.2 delivery: PASSED; ' + str(work / 'report.json'))

if __name__ == '__main__':
    main()
