[CmdletBinding()]
param([string]$JavaHome='', [string]$RunName='', [switch]$SkipBuild)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome
if(-not $RunName){$RunName='b052-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($RunName -notmatch '^[A-Za-z0-9-]+$'){throw 'Use a simple fresh run name'}
$work=Join-Path $root "target/reconciliation/$RunName"
if(Test-Path -LiteralPath $work){throw 'Use a fresh reconciliation run name'}
New-Item -ItemType Directory -Path $work | Out-Null
$report=[ordered]@{status='RUNNING';scope='actual MySQL + controlled A + independent simulated channel + two JVMs; actual A is a separate batch';phases=@();oldProtectedRowsMissingOrChanged=$null}
$names=@('B_DATABASE_ENABLED','B_DATABASE_URL','B_DATABASE_USERNAME','B_DATABASE_PASSWORD','B_DATABASE_SCOPE','B_MIGRATION_USERNAME','B_MIGRATION_PASSWORD','B_IDENTITY_ORIGIN','B_IDENTITY_SECURE_COOKIES','B_IDENTITY_KEY_ID','B_IDENTITY_PRIVATE_KEY_FILE','B_IDENTITY_PUBLIC_KEY_FILE','B_PRODUCT_EVENT_PRODUCER','B_PRODUCT_EVENT_SOURCE','B_PRODUCT_EVENT_CHANNEL','B_PAYMENT_WORK')
$previous=@{};foreach($name in $names){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
function Snapshot([string]$label){
 $record=Import-Clixml -LiteralPath (Join-Path $root '.local/b02-test-database.credentials.xml')
 $query=@'
SET SESSION TRANSACTION READ ONLY;
START TRANSACTION WITH CONSISTENT SNAPSHOT;
SELECT CONCAT('work:',work_id,':',SHA2(evidence,256),':',evidence_hash) FROM b_trade_work;
SELECT CONCAT('money:',payment_id,':',funds_state,':',COALESCE(success_attempt_id,'NULL'),':',COALESCE(paid_at_ms,'NULL'),':',COALESCE(success_hash,'NULL')) FROM b_payment WHERE funds_state IN ('SUCCEEDED','UNKNOWN');
SELECT CONCAT('hold:',order_id,':',state) FROM b_inventory_reservation WHERE state='HELD';
SELECT CONCAT('guard:',user_id,':',goods_id,':',active_order_id) FROM b_purchase_guard WHERE active_order_id IS NOT NULL;
SELECT CONCAT('channel:',payment_id,':',gate,':',COALESCE(success_attempt_id,'NULL')) FROM b_sim_payment WHERE gate='PAID';
COMMIT;
'@
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
 $jar=Join-Path $root 'zj-market-verification/target/zj-market-verification.jar'
 $hash=(Get-FileHash -LiteralPath $jar).Hash
 foreach($mode in @('verify','recover')){
  & $jdk.Java -jar $jar --reconciliation $mode *> "$work/$mode.log"
  if($LASTEXITCODE -ne 0){throw "Reconciliation $mode failed; inspect ignored log"}
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
 $report.status='PASSED'
}catch{$report.status='FAILED';$report.errorType=$_.Exception.GetType().FullName;$report.error=$_.Exception.Message;throw}
finally{$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$work/report.json";foreach($name in $names){Restore-BEnvironmentVariable $name $previous[$name]};Pop-Location}
Write-Host "B-05.2 MySQL/controlled-channel/JVM acceptance: $($report.status)"
