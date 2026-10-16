"""Publish a sanitized TD00 evidence index; never include passwords or jar bytes."""
import argparse
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))


def main(args):
    baseline=read(args.baseline/'baseline.json')
    contract=read(args.contract/'acceptance.json')
    static=read(args.contract/'static-checks.json')
    fixture=read(args.fixture)
    verified=read(args.verified)
    lock=read(ROOT/'docs/team-discovery-contract-lock.json')
    assert contract['status']=='PASSED_CONTRACT_BASELINE'
    assert static['status']=='PASSED_CONTRACT_STATIC_CHECKS'
    assert verified['status']=='PASSED_PREPARED_FIXTURE_AND_READONLY_BASELINE'
    assert fixture['originalFinancialUnchanged']
    assert contract['contractSha256']==lock['sha256']==sha(args.contract/'contract.jar')
    reports=[args.baseline/'baseline.json',args.contract/'acceptance.json',args.contract/'static-checks.json',
             args.contract/'java8.log',args.contract/'java21.log',args.fixture,args.verified]
    payload={'stage':'TD-00','status':'PASSED_BASELINE_AND_CONTRACT_FREEZE','stageCompletion':True,
             'generatedAt':datetime.now(timezone.utc).isoformat(),
             'scope':'Contract DTO/artifact, wire design, fresh isolated data preparation and real B06 read-only inventory only',
             'decisions':{'TD-D1':'At least one payment accepted by A before listing','TD-D2':'Authenticated users only'},
             'repositories':{n:{k:v for k,v in r.items() if k in ['path','head','branch','status']} for n,r in baseline['repositories'].items()},
             'oldArtifacts':baseline['artifacts'],'legacyEmbeddedContractsIdentical':baseline['deployedContractsIdentical'],
             'oldMigrations':{n:{p:h for p,h in r['sourceSha256'].items() if '/migration/' in p or '/migrations/' in p} for n,r in baseline['repositories'].items() if n in ['a','b']},
             'newContract':{k:lock[k] for k in ['coordinate','sha256','bytes','javaBytecodeMajor','published','installed']},
             'contractChecks':contract,'staticChecks':static['count'],'runtimeAndFixtureChecks':verified['count'],
             'runtime':verified['runtime'],'actualRuntimeJarSha256':verified['actualJarSha256'],
             'fixture':{k:fixture[k] for k in ['runName','schemas','schemaProvenance','source','channel','goodsId','activityId','activityWindow','productVersion','targetCount','teamValidMinutes','stock','sync','business']},
             'fixtureAccountCount':4,'fixtureRoleCount':5,'originalFinancialTables':fixture['protectedFinancialTables'],
             'originalFinancialBefore':fixture['financialBefore'],'originalFinancialAfter':fixture['financialAfter'],
             'originalFinancialUnchanged':fixture['originalFinancialUnchanged'],
             'originalWholeDatabaseBytesUnchanged':fixture['originalDataUnchanged'],
             'readonlyFixtureRowsUnchanged':verified['before']==verified['after'],
             'evidence':{p.resolve().relative_to(ROOT).as_posix():sha(p) for p in reports},
             'failedOrSuperseded':['td00-20261014-01: sandbox access; preserved','td00-20261014-02 initial runtime enumeration included stopped mq-permissions; verified final snapshot supersedes only runtime verdict','fixture-20261014-01: seed constraints; FAILED retained','fixture-20261014-02: all-db hash assertion; FAILED retained','fixture-verify-01: incorrect amount source; failed record retained'],
             'limitations':['No discovery Provider, authorization whitelist, index migration, B HTTP or UI implemented',
                            'No discovery TLS/Triple/MQ/payment/full transaction acceptance performed',
                            'DDL-cloned isolated schemas have empty Flyway history; not certified runtime databases',
                            'Product has no fabricated sync confirmation; real publication/sync belongs to next stages',
                            'No new contract installed/published and no existing consumer dependency or image upgraded',
                            'Online whole databases changed between observations; stable money/order/stock/team facts unchanged',
                            'New fixture runtime accounts and migration-based startup still required before TD01/02 live integration'],
             'gitPublished':False,'nextStage':'TD-01'}
    if args.output.exists():raise ValueError('Do not overwrite historical summary')
    args.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':payload['status'],'staticChecks':static['count'],'runtimeChecks':verified['count'],'output':str(args.output)}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['baseline','contract','fixture','verified','output']:p.add_argument('--'+name,type=Path,required=True)
    main(p.parse_args())
