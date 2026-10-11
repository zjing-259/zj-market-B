[CmdletBinding()]
param([string]$JavaHome='',[string]$AJavaHome='D:/Dev_tools/2.environment/jdk/jdk8',[string]$RunName='',[string]$CredentialSource='D:/Java/zj-market-b-04')
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome
if(-not $RunName){$RunName='b050-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($RunName -notmatch '^[A-Za-z0-9-]+$'){throw 'Use a simple unique run name'}
if((& git -C $root branch --show-current) -ne 'b-05'){throw 'Run in the b-05 worktree'}
$work=Join-Path $root "target/b05-baseline/$RunName"
if(Test-Path -LiteralPath $work){throw 'Use a new batch; previous evidence is retained'}
New-Item -ItemType Directory -Path $work | Out-Null
$original=@{};Get-ChildItem Env: | ForEach-Object {$original[$_.Name]=$_.Value}
$defaultJava=(& java -version 2>&1 | Out-String).Trim()
$report=[ordered]@{stage='B-05.0';status='RUNNING';runName=$RunName;head=(& git -C $root rev-parse HEAD);steps=@();evidence=@{};artifacts=@{};scope='New worktree baseline; actual A/RPC/MQ and simulated payment success; no B05 refund or reconciliation executor'}
$checkpoints=@{}
foreach($repo in @('zj-market','zj-market-b-04','group-buy-market')){
 $path=Join-Path (Split-Path $root -Parent) $repo
 $checkpoints[$path]=@{status=((& git -C $path status --porcelain) -join "`n");head=(& git -C $path rev-parse HEAD);roadmap=$(if(Test-Path "$path/docs/development-roadmap.md"){(Get-FileHash "$path/docs/development-roadmap.md").Hash}else{''})}
}
function Test-Port([int]$port){$c=[Net.Sockets.TcpClient]::new();try{return $c.ConnectAsync('127.0.0.1',$port).Wait(500)}catch{return $false}finally{$c.Dispose()}}
function Step([string]$name,[scriptblock]$action){[IO.File]::WriteAllText("$work/progress.txt",$name);try{& $action *> "$work/$name.log"}catch{$script:report.failedStep=$name;throw};$script:report.steps+=@($name)}
function Save-Report([string]$name,[string]$path){
 $file=Get-Item -LiteralPath $path; $body=[IO.File]::ReadAllText($file.FullName)
 $pass=if($file.Extension -eq '.json'){($body|ConvertFrom-Json).status -eq 'PASSED'}else{$body.Contains('status=PASSED')}
 if(-not $pass){throw "Non-passing evidence: $name"}
 $copy="$work/$name$($file.Extension)";if([IO.Path]::GetFullPath($copy) -ne [IO.Path]::GetFullPath($file.FullName)){Copy-Item -LiteralPath $file.FullName -Destination $copy}
 $script:report.evidence[$name]=@{source=$file.FullName;sha256=(Get-FileHash $copy).Hash}
}
function Protected-Snapshot([string]$label){
 # Password is sent only over stdin, never in process arguments, reports or shell source.
 $c=Import-Clixml -LiteralPath "$root/.local/b02-test-database.credentials.xml"
 if($c.Runtime.UserName -ne 'zj_market_b02_test_app' -or $c.Scope -ne 'b02-test' -or $c.Runtime.GetNetworkCredential().Password -notmatch '^[0-9a-f]{64}$'){throw 'Unexpected isolated credentials'}
 $sql=@'
SET SESSION TRANSACTION READ ONLY;
START TRANSACTION WITH CONSISTENT SNAPSHOT;
SELECT CONCAT('work:',work_id,':',SHA2(evidence,256),':',evidence_hash) FROM b_trade_work;
SELECT CONCAT('money:',payment_id,':',funds_state,':',COALESCE(success_attempt_id,'NULL'),':',COALESCE(paid_at_ms,'NULL'),':',COALESCE(success_hash,'NULL')) FROM b_payment WHERE funds_state IN ('SUCCEEDED','UNKNOWN');
SELECT CONCAT('hold:',order_id,':',state) FROM b_inventory_reservation WHERE state='HELD';
SELECT CONCAT('guard:',user_id,':',goods_id,':',active_order_id) FROM b_purchase_guard WHERE active_order_id IS NOT NULL;
SELECT CONCAT('channel:',attempt_id,':',state,':',COALESCE(paid_at_ms,'NULL'),':',request_hash) FROM b_sim_attempt WHERE state IN ('SUCCEEDED','UNKNOWN');
COMMIT;
'@
 $inputText=$c.Runtime.GetNetworkCredential().Password+"`n"+$sql
 $rows=@($inputText | & docker exec -i mysql sh -c 'read -r MYSQL_PWD; export MYSQL_PWD; exec mysql -uzj_market_b02_test_app zj_market_b02_test --batch --skip-column-names' 2> "$work/$label-db.stderr.log")
 if($LASTEXITCODE -ne 0){throw 'Protected read-only snapshot failed; inspect ignored log'}
 $rows | Sort-Object | Set-Content -LiteralPath "$work/$label-protected.txt"
 return ,$rows
}
Push-Location $root
$failed=$true
try{
 foreach($port in @(50051,18091,18092,5173)){if(Test-Port $port){throw "Port $port occupied; do not stop unrelated processes"}}
 Step credentials {
  foreach($relative in @('database.credentials.xml','b02-test-database.credentials.xml','b02-test-keys/private.pem','b02-test-keys/public.pem')){
   $destination=Join-Path $root ".local/$relative"; $source=Join-Path $CredentialSource ".local/$relative"
   & git check-ignore --quiet --no-index -- $destination;if($LASTEXITCODE -ne 0){throw 'Local material must be ignored'}
   if(-not(Test-Path -LiteralPath $destination)){New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null;Copy-Item -LiteralPath $source -Destination $destination}
  }
  foreach($name in @('database.credentials.xml','b02-test-database.credentials.xml')){$c=Import-Clixml ".local/$name";if(-not $c.Runtime.GetNetworkCredential().Password -or -not $c.Migration.GetNetworkCredential().Password){throw 'DPAPI decode failed'}}
 }
 $before=Protected-Snapshot before
 Step build {Invoke-BMaven -JavaHome $jdk.Home -Arguments @('-B','package')}
 Step frontend {
  & npm ci --prefix frontend;if($LASTEXITCODE -ne 0){throw 'Locked frontend install failed'}
  & npm run build --prefix frontend;if($LASTEXITCODE -ne 0){throw 'Frontend type/build failed'}
 }
 foreach($file in @('zj-market-app/target/zj-market-app-exec.jar','zj-market-verification/target/zj-market-verification.jar','frontend/package-lock.json','../group-buy-market/docs/ab-api-contract.md','../group-buy-market/group-buy-market-app/target/group-buy-market-app.jar')+@(Get-ChildItem zj-market-infrastructure/src/main/resources/db/migration/*.sql | ForEach-Object {$_.FullName})){$report.artifacts[$file]=(Get-FileHash -LiteralPath $file).Hash}
 Step normal-runtime {
  & ./scripts/start-b.ps1 -JavaHome $jdk.Home -SkipBuild -ApplicationArguments @('--spring.main.web-application-type=none','--b.identity.enabled=false','--b.product.enabled=false','--b.inventory.enabled=false','--b.order.enabled=false','--b.trade.enabled=false','--b.payment.enabled=false','--b.trade.events-enabled=false','--b.trial.enabled=false','--b.sync.enabled=false','--b.infrastructure.database.enabled=false','--b.infrastructure.rpc.enabled=false','--b.infrastructure.mq.enabled=false')
 }
 if(-not([IO.File]::ReadAllText("$work/normal-runtime.log") -match 'using Java 21\.')){throw 'Normal runtime JDK not proven'}
 $entries=& (Join-Path $jdk.Home 'bin/jar.exe') tf zj-market-app/target/zj-market-app-exec.jar
 if($LASTEXITCODE -ne 0 -or @($entries | Where-Object {$_ -match 'verification|flyway'}).Count){throw 'Normal package boundary failed'}
 # The wrapper performs explicit Flyway validation/temporary privilege probes in both B schemas.
 Step real-a {& ./docs/tests/run-b03-readiness.ps1 -JavaHome $jdk.Home -AJavaHome $AJavaHome -RunName "$RunName-live" -WithFulfillment -SkipBuild}
 $live="target/b03-readiness/$RunName-live"
 foreach($file in @('report.json','baseline.json','verify.txt','fulfillment.txt','fulfillment.json','trade-recovery.json')){Save-Report "real-a-$($file.Replace('.','-'))" "$live/$file"}
 Copy-Item "$live/provenance.txt" "$work/real-a-provenance.txt"
 foreach($scope in @('database.credentials.xml','b02-test-database.credentials.xml')){
  foreach($mode in @('migrate','verify')){Save-Report "$scope-$mode" "$live/$scope-$mode.txt"}
 }
 Step settlement {& ./docs/tests/run-b04-settlement.ps1 -JavaHome $jdk.Home -RunName "$RunName-settlement" -SkipBuild}
 foreach($name in @('verify','recover','notification-lease')){Save-Report "settlement-$name" "target/settlement/$RunName-settlement/$name.txt"}
 Step handoff {& ./docs/tests/run-b04-handoff.ps1 -JavaHome $jdk.Home -RunName "$RunName-handoff" -SkipBuild}
 Save-Report handoff "target/b04-handoff/$RunName-handoff/snapshot.json"
 $after=Protected-Snapshot after
 $present=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal);foreach($row in $after){[void]$present.Add($row)}
 $missing=@($before|Where-Object {-not $present.Contains($_)});$report.protectedRowsBefore=$before.Count;$report.protectedRowsAfter=$after.Count;$report.oldProtectedRowsMissingOrChanged=$missing.Count
 if($missing.Count){throw 'Old protected work/money/hold/guard facts changed; inspect local snapshots'}
 foreach($entry in $report.artifacts.GetEnumerator()){if((Get-FileHash -LiteralPath $entry.Key).Hash -ne $entry.Value){throw 'Baseline artifacts changed during verification'}}
 Step delivery-audit {& ./docs/tests/check-b03-delivery.ps1 -ReportFile "$work/delivery-audit.json"}
 Save-Report delivery-audit "$work/delivery-audit.json"
 $failed=$false
}catch{
 $report.failureType=$_.Exception.GetType().Name
 throw
}finally{
 $restored=$true;$current=@{};Get-ChildItem Env: | ForEach-Object {$current[$_.Name]=$_.Value}
 foreach($name in @($original.Keys)+@($current.Keys)|Sort-Object -Unique){if($original[$name] -cne $current[$name]){$restored=$false}}
 $report.environmentRestored=$restored;$report.defaultJavaUnchanged=((& java -version 2>&1 | Out-String).Trim() -ceq $defaultJava)
 $report.ownedPortsReleased=@(@(50051,18091,18092,5173)|Where-Object {Test-Port $_}).Count -eq 0
 $report.otherWorktreesPreserved=$true
 foreach($entry in $checkpoints.GetEnumerator()){
  $path=$entry.Key;$prior=$entry.Value
  if(((& git -C $path status --porcelain) -join "`n") -cne $prior.status -or (& git -C $path rev-parse HEAD) -ne $prior.head){$report.otherWorktreesPreserved=$false}
  if($prior.roadmap -and (Get-FileHash "$path/docs/development-roadmap.md").Hash -ne $prior.roadmap){$report.otherWorktreesPreserved=$false}
 }
 $report.status=if(-not $failed -and $restored -and $report.defaultJavaUnchanged -and $report.ownedPortsReleased -and $report.otherWorktreesPreserved){'PASSED'}else{'FAILED'}
 $report.finishedAt=[DateTime]::UtcNow.ToString('o');$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$work/report.json"
 Pop-Location
 if($report.status -ne 'PASSED'){throw "Baseline incomplete; evidence retained at $work"}
}
Write-Host "B-05.0 baseline: PASSED; report=$work/report.json"
