[CmdletBinding()]
param([string]$JavaHome='C:/Program Files/Java/jdk-21',[Parameter(Mandatory)][string]$Prefix)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
if($Prefix -notmatch '^b055-[A-Za-z0-9-]+$'){throw 'Use a fresh B055 regression prefix'}
$work=Join-Path $root "target/refund/$Prefix-final"
if(Test-Path $work){throw 'Use a fresh final batch'}
New-Item -ItemType Directory -Path $work|Out-Null
$actualOrder=''
$report=[ordered]@{status='RUNNING';verificationJarSha256=(Get-FileHash "$root/zj-market-verification/target/zj-market-verification.jar").Hash}
function Snapshot([string]$label){
 $record=Import-Clixml -LiteralPath (Join-Path $root '.local/b02-test-database.credentials.xml')
 $query=@'
SET SESSION TRANSACTION READ ONLY;
START TRANSACTION WITH CONSISTENT SNAPSHOT;
SELECT CONCAT('outbox-wire:',event_id,':',SHA2(body,256),':',body_hash) FROM b_trade_outbox;
SELECT CONCAT('refund-version:',attempt_id,':',pending_version,':',pending_hash,':',COALESCE(result_version,'NULL'),':',COALESCE(result_hash,'NULL')) FROM b_refund_attempt;
SELECT CONCAT('work:',work_id,':',SHA2(evidence,256),':',evidence_hash) FROM b_trade_work;
SELECT CONCAT('money:',payment_id,':',funds_state,':',COALESCE(success_attempt_id,'NULL'),':',COALESCE(paid_at_ms,'NULL'),':',COALESCE(success_hash,'NULL')) FROM b_payment WHERE funds_state IN ('SUCCEEDED','UNKNOWN');
SELECT CONCAT('hold:',order_id,':',state) FROM b_inventory_reservation WHERE state='HELD';
SELECT CONCAT('guard:',user_id,':',goods_id,':',active_order_id) FROM b_purchase_guard WHERE active_order_id IS NOT NULL;
SELECT CONCAT('refund:',refund_id,':',funds_status,':',snapshot_hash,':',COALESCE(eligibility_proof_hash,'NULL')) FROM b_refund;
SELECT CONCAT('channel:',payment_id,':',gate,':',COALESCE(success_attempt_id,'NULL')) FROM b_sim_payment WHERE gate='PAID';
COMMIT;
'@
 if($actualOrder){$query=$query.Replace('FROM b_refund;',"FROM b_refund WHERE order_id<>'$actualOrder';")}
 $inputText=$record.Runtime.GetNetworkCredential().Password+"`n"+$query
 $rows=@($inputText | & docker exec -i mysql sh -c 'read -r MYSQL_PWD; export MYSQL_PWD; exec mysql -uzj_market_b02_test_app zj_market_b02_test --batch --skip-column-names' 2> "$work/$label-db.stderr.log")
 if($LASTEXITCODE -ne 0){throw 'Protected snapshot failed'}
 $rows | Sort-Object | Set-Content -LiteralPath "$work/$label-protected.txt"
 return ,$rows
}
Push-Location $root
try{
 $before=Snapshot before
 ./docs/tests/run-b04-payment-closing.ps1 -JavaHome $JavaHome -RunName "$Prefix-closing-regression" -SkipBuild *> "$work/closing.log"
 ./docs/tests/run-b04-settlement.ps1 -JavaHome $JavaHome -RunName "$Prefix-settlement-regression" -SkipBuild *> "$work/settlement.log"
 ./docs/tests/run-b04-fulfillment.ps1 -JavaHome $JavaHome -RunName "$Prefix-fulfillment-regression" -SkipBuild *> "$work/fulfillment.log"
 ./docs/tests/run-b04-handoff.ps1 -JavaHome $JavaHome -RunName "$Prefix-handoff" -SkipBuild *> "$work/handoff.log"
 ./docs/tests/run-b05-refund-startup.ps1 -JavaHome $JavaHome -RunName "$Prefix-startup" *> "$work/startup.log"
 $after=Snapshot after
 $present=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal);foreach($row in $after){[void]$present.Add($row)}
 $missing=@($before|Where-Object {-not $present.Contains($_)})
 $report.oldProtectedRowsMissingOrChanged=$missing.Count
 if($missing.Count){throw 'Regression changed old protected facts'}
 if((Get-FileHash "$root/zj-market-verification/target/zj-market-verification.jar").Hash -ne $report.verificationJarSha256){throw 'Regression verification package changed'}
 $report.status='PASSED'
}catch{$report.status='FAILED';$report.error=$_.Exception.Message;throw}
finally{$report|ConvertTo-Json -Depth 6|Set-Content "$work/report.json";Pop-Location}
Write-Host "B-05.5 original closing/settlement/fulfillment/readonly audit/default startup: $($report.status)"
