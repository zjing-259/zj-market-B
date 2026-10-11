[CmdletBinding()]
param([string]$JavaHome='', [string]$RunName='', [switch]$SkipBuild,[string]$ActualBatch='')
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome
if(-not $RunName){$RunName='b054-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($RunName -notmatch '^[A-Za-z0-9-]+$'){throw 'Use a simple fresh run name'}
$work=Join-Path $root "target/refund/$RunName"
if(Test-Path -LiteralPath $work){throw 'Use a fresh refund run name'}
New-Item -ItemType Directory -Path $work | Out-Null
$report=[ordered]@{status='RUNNING';scope='actual MySQL + controlled A eligibility + independent simulated refund channel + two JVMs; refund Outbox/strict receipts included; release remains later';phases=@();oldProtectedRowsMissingOrChanged=$null}
$names=@('B_DATABASE_ENABLED','B_DATABASE_URL','B_DATABASE_USERNAME','B_DATABASE_PASSWORD','B_DATABASE_SCOPE','B_MIGRATION_USERNAME','B_MIGRATION_PASSWORD','B_IDENTITY_ORIGIN','B_IDENTITY_SECURE_COOKIES','B_IDENTITY_KEY_ID','B_IDENTITY_PRIVATE_KEY_FILE','B_IDENTITY_PUBLIC_KEY_FILE','B_PRODUCT_EVENT_PRODUCER','B_PRODUCT_EVENT_SOURCE','B_PRODUCT_EVENT_CHANNEL','B_PAYMENT_WORK','B_REFUND_ACTUAL_MANIFEST')
$actualOrder=''
if($ActualBatch){
 if($ActualBatch -notmatch '^b053-[A-Za-z0-9-]+$'){throw 'Only fresh current-stage actual A batches are accepted'}
 $manifest=Join-Path $root "target/b03-readiness/$ActualBatch/reconciliation-restart.json"
 $actualOrder=(Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json).paidOrder
 if($actualOrder -notmatch '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'){throw 'Invalid owned actual order'}
 $actualReport=Get-Content (Join-Path $root "target/b03-readiness/$ActualBatch/report.json") -Raw | ConvertFrom-Json
 if($actualReport.status -ne 'PASSED' -or -not $actualReport.ownedPortsReleased){throw 'Actual A acceptance/cleanup must pass first'}
 $rpcPort=if($actualReport.providerRpcPort){[int]$actualReport.providerRpcPort}else{50051};$httpPort=if($actualReport.providerHttpPort){[int]$actualReport.providerHttpPort}else{18091}
 if(Get-NetTCPConnection -LocalPort $rpcPort,$httpPort -State Listen -ErrorAction SilentlyContinue){throw 'Actual refund expects the readiness-owned A provider already stopped'}
 $report.scope='fresh actual-A complete team eligibility, provider stopped, RPC/MQ disabled refund JVM'
 $report.authorizedRefundOrder=$actualOrder
}
$previous=@{};foreach($name in $names){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
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
 if(-not $SkipBuild){Invoke-BMaven -JavaHome $jdk.Home -Arguments @('-B','package') *> "$work/build.log"}
 foreach($schema in @('test','development')){
  & ./scripts/provision-b-database.ps1 -TestDatabase:($schema -eq 'test') -JavaHome $jdk.Home -SkipBuild *> "$work/$schema-provision.log"
  Copy-Item target/database/migrate.txt "$work/$schema-migrate.txt"
  Copy-Item target/database/verify.txt "$work/$schema-permissions.txt"
  $report.phases+=@{name="$schema-migration-and-permissions";status='PASSED'}
 }
 $c=Import-Clixml -LiteralPath .local/b02-test-database.credentials.xml
 Restore-BEnvironmentVariable B_DATABASE_URL $c.Url
 Restore-BEnvironmentVariable B_DATABASE_USERNAME $c.Runtime.UserName
 Restore-BEnvironmentVariable B_DATABASE_PASSWORD $c.Runtime.GetNetworkCredential().Password
 Restore-BEnvironmentVariable B_DATABASE_SCOPE $c.Scope
 Restore-BEnvironmentVariable B_DATABASE_ENABLED true
 Restore-BEnvironmentVariable B_MIGRATION_USERNAME $null
 Restore-BEnvironmentVariable B_MIGRATION_PASSWORD $null
 Restore-BEnvironmentVariable B_IDENTITY_ORIGIN 'http://127.0.0.1:5173'
 Restore-BEnvironmentVariable B_IDENTITY_SECURE_COOKIES false
 Restore-BEnvironmentVariable B_IDENTITY_KEY_ID b02-test
 Restore-BEnvironmentVariable B_IDENTITY_PRIVATE_KEY_FILE (Join-Path $root '.local/b02-test-keys/private.pem')
 Restore-BEnvironmentVariable B_IDENTITY_PUBLIC_KEY_FILE (Join-Path $root '.local/b02-test-keys/public.pem')
 Restore-BEnvironmentVariable B_PRODUCT_EVENT_PRODUCER 'zj-market'
 Restore-BEnvironmentVariable B_PRODUCT_EVENT_SOURCE s01
 Restore-BEnvironmentVariable B_PRODUCT_EVENT_CHANNEL c01
 Restore-BEnvironmentVariable B_PAYMENT_WORK $work
 if($ActualBatch){Restore-BEnvironmentVariable B_REFUND_ACTUAL_MANIFEST $manifest}
 $jar=Join-Path $root 'zj-market-verification/target/zj-market-verification.jar'
 $hash=(Get-FileHash -LiteralPath $jar).Hash
 foreach($mode in $(if($ActualBatch){@('actual')}else{@('verify','recover')})){
  if($ActualBatch){& $jdk.Java -jar $jar --refund-actual *> "$work/$mode.log"}else{& $jdk.Java -jar $jar --refund-sync $mode *> "$work/$mode.log"}
  if($LASTEXITCODE -ne 0){throw "Refund $mode failed; inspect ignored log"}
  if(-not((Get-Content "$work/$mode.txt") -contains 'status=PASSED')){throw 'Missing acceptance report'}
  $report.phases+=@{name=$mode;status='PASSED'}
 }
 if((Get-FileHash -LiteralPath $jar).Hash -ne $hash){throw 'Verification jar changed'}
 $report.verificationJarSha256=$hash
 $after=Snapshot after
 $present=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal);foreach($row in $after){[void]$present.Add($row)}
 $missing=@($before|Where-Object {-not $present.Contains($_)})
 $report.oldProtectedRowsBefore=$before.Count;$report.oldProtectedRowsAfter=$after.Count;$report.oldProtectedRowsMissingOrChanged=$missing.Count
 if($missing.Count){throw 'Old protected funds/work/HELD/guard/channel facts changed'}
 if(-not((Get-Content "$work/sync.txt") -contains 'status=PASSED')){throw 'Missing refund sync acceptance'}
 $report.status='PASSED'
}catch{$report.status='FAILED';$report.errorType=$_.Exception.GetType().FullName;$report.error=$_.Exception.Message;throw}
finally{$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$work/report.json";foreach($name in $names){Restore-BEnvironmentVariable $name $previous[$name]};Pop-Location}
Write-Host "B-05.4 refund sync/controlled-A/JVM acceptance: $($report.status)"
