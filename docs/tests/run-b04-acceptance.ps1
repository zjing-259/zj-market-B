[CmdletBinding()]
param([string]$JavaHome='', [string]$AJavaHome='D:/Dev_tools/2.environment/jdk/jdk8', [string]$RunName='', [string]$PythonExecutable='python', [switch]$SkipBuild)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome
if($PSVersionTable.PSVersion.Major -lt 7){throw 'Joint acceptance requires PowerShell 7.'}
if(-not $RunName){$RunName='b046-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($RunName -notmatch '^[A-Za-z0-9-]+$'){throw 'Use a simple unique run name.'}
$work=Join-Path $root "target/b04-acceptance/$RunName"
if(Test-Path -LiteralPath $work){throw 'Use a new batch; previous evidence is retained.'}
New-Item -ItemType Directory -Path $work | Out-Null
$started=[DateTime]::UtcNow
$original=@{};Get-ChildItem Env: | ForEach-Object {$original[$_.Name]=$_.Value}
$defaultJava=(& java -version 2>&1 | Out-String).Trim()
$result=[ordered]@{stage='B-04.6';status='RUNNING';runName=$RunName;java=$jdk.Home;steps=@();evidence=@{};artifacts=@{};simulationOnly=$true;checkoutDefaultEnabled=$false;refundExecutionImplemented=$false}
function Test-Port([int]$port){$c=[Net.Sockets.TcpClient]::new();try{return $c.ConnectAsync('127.0.0.1',$port).Wait(500)}catch{return $false}finally{$c.Dispose()}}
function Step([string]$name,[scriptblock]$action){
 [IO.File]::WriteAllText("$work/progress.txt",$name)
 try {& $action *> "$work/$name.log"}catch{$script:result.failedStep=$name;throw}
 $script:result.steps+=@($name)
}
function Save-Report([string]$name,[string]$path){
 $file=Get-Item -LiteralPath $path -ErrorAction Stop
 if($file.LastWriteTimeUtc -lt $started.AddSeconds(-2)){throw "Stale evidence refused: $name"}
 $body=[IO.File]::ReadAllText($file.FullName)
 if($file.Extension -eq '.json'){$pass=($body | ConvertFrom-Json).status -eq 'PASSED'}else{$pass=$body.Contains('status=PASSED')}
 if(-not $pass){throw "Non-passing evidence refused: $name"}
 $copy=Join-Path $work ($name+$file.Extension);if($copy -ne $file.FullName){Copy-Item -LiteralPath $file.FullName -Destination $copy}
 $script:result.evidence[$name]=@{file=$copy;source=$file.FullName;sha256=(Get-FileHash -LiteralPath $copy).Hash}
}
Push-Location $root
$failed=$true
try{
 foreach($port in @(50051,18091,18092,5173)){if(Test-Port $port){throw "Port $port occupied; no unrelated process will be stopped."}}
 if(-not $SkipBuild){Step build {Invoke-BMaven -JavaHome $jdk.Home -Arguments @('-B','package')};$summary=[regex]::Matches([IO.File]::ReadAllText("$work/build.log"),'Tests run: (\d+), Failures: 0, Errors: 0, Skipped: 0');if(-not $summary.Count){throw 'Passing unit test summary missing'};$result.unitTests=[int]$summary[-1].Groups[1].Value}else{$result.unitTests='not run (SkipBuild)'}
 foreach($artifact in @('zj-market-app/target/zj-market-app-exec.jar','zj-market-app/target/zj-market-app.jar','zj-market-verification/target/zj-market-verification.jar','frontend/package-lock.json','../group-buy-market/docs/ab-api-contract.md') + @(Get-ChildItem 'zj-market-infrastructure/src/main/resources/db/migration/*.sql' | ForEach-Object {$_.FullName})){$result.artifacts[$artifact]=(Get-FileHash -LiteralPath $artifact).Hash}
 Step normal-runtime {
  & (Join-Path $root 'scripts/start-b.ps1') -JavaHome $jdk.Home -SkipBuild -ApplicationArguments @('--spring.main.web-application-type=none','--b.identity.enabled=false','--b.product.enabled=false','--b.inventory.enabled=false','--b.order.enabled=false','--b.trade.enabled=false','--b.trial.enabled=false','--b.sync.enabled=false','--b.infrastructure.database.enabled=false','--b.infrastructure.rpc.enabled=false','--b.infrastructure.mq.enabled=false')
 }
 if(-not([IO.File]::ReadAllText("$work/normal-runtime.log") -match 'using Java 21\.')){throw 'Ordinary runtime did not prove target JDK.'}
 Step development-schema {& (Join-Path $root 'scripts/provision-b-database.ps1') -JavaHome $jdk.Home -SkipBuild}
 Copy-Item target/database/migrate.txt "$work/development-migrate.txt";Save-Report development-permissions 'target/database/verify.txt'
 Step test-schema {& (Join-Path $root 'scripts/provision-b-database.ps1') -TestDatabase -JavaHome $jdk.Home -SkipBuild}
 Copy-Item target/database/migrate.txt "$work/test-migrate.txt";Save-Report test-permissions 'target/database/verify.txt'
 foreach($phase in @('payments','settlement','payment-closing','fulfillment')){
  Step $phase {& (Join-Path $PSScriptRoot "run-b04-$phase.ps1") -JavaHome $jdk.Home -RunName "$RunName-$phase" -SkipBuild}
  foreach($mode in @('verify','recover')){Save-Report "$phase-$mode" "target/$phase/$RunName-$phase/$mode.txt"}
 }
 foreach($phase in @('orders','closes','joint-faults')){
  Step "b03-$phase" {& (Join-Path $PSScriptRoot "run-b03-$phase.ps1") -JavaHome $jdk.Home -SkipBuild}
  $file=if($phase -eq 'joint-faults'){"target/$phase/verify.json"}else{"target/$phase/verify.txt"}
  Save-Report "b03-$phase" $file
 }
 foreach($phase in @('fulfillment','settlement','payment-closing','joint-faults')){
  $switches=@{WithFulfillment='fulfillment';WithSettlement='settlement';WithPaymentClosing='payment-closing';WithJointFaults='joint-faults'}
  $arguments=@{JavaHome=$jdk.Home;AJavaHome=$AJavaHome;RunName="$RunName-live-$phase";SkipBuild=$true}
  foreach($key in $switches.Keys){if($switches[$key] -eq $phase){$arguments[$key]=$true}}
  Step "real-a-$phase" {& (Join-Path $PSScriptRoot 'run-b03-readiness.ps1') @arguments}
  $live="target/b03-readiness/$RunName-live-$phase"
  Save-Report "real-a-$phase" "$live/report.json"
  $files=switch($phase){
   fulfillment {@('fulfillment.txt','fulfillment.json','trade-recovery.json')}
   settlement {@('settlement.txt','settlement.json','trade-recovery.json')}
   payment-closing {@('payment-closing.txt','payment-closing.json','trade-recovery.json')}
   joint-faults {@('trade-recovery.json','close-recovery.json','close-recover.txt','close-outage.txt','close-outage-recovery.json','a-outage-processes.json')}
  }
  foreach($file in $files){Save-Report "real-a-$phase-$($file.Replace('.','-'))" "$live/$file"}
  Copy-Item "$live/provenance.txt" "$work/real-a-$phase-provenance.txt"
 }
 foreach($phase in @('payments','fulfillment')){
  Step "$phase-browser" {& (Join-Path $PSScriptRoot "run-b04-$phase-browser.ps1") -JavaHome $jdk.Home -RunName "$RunName-$phase-browser" -SkipBuild}
  Save-Report "$phase-browser" "target/payments/$RunName-$phase-browser/browser.json"
 }
 Step handoff-snapshot {& (Join-Path $PSScriptRoot 'run-b04-handoff.ps1') -JavaHome $jdk.Home -RunName "$RunName-handoff" -SkipBuild}
 Save-Report handoff-snapshot "target/b04-handoff/$RunName-handoff/snapshot.json"
 $entries=& (Join-Path $jdk.Home 'bin/jar.exe') tf zj-market-app/target/zj-market-app-exec.jar
 if($LASTEXITCODE -ne 0 -or @($entries | Where-Object {$_ -match 'verification|flyway'}).Count){throw 'Ordinary package contains verification/migration dependency.'}
 foreach($entry in $result.artifacts.GetEnumerator()){if((Get-FileHash -LiteralPath $entry.Key).Hash -ne $entry.Value){throw 'Artifacts changed during joint acceptance.'}}
 Step contract-validation {
  & $PythonExecutable -X utf8 (Join-Path $PSScriptRoot 'validate-b04-contracts.py') --run-name $RunName
  if($LASTEXITCODE -ne 0){throw 'Contract/delivery boundary validation failed'}
 }
 Save-Report contract-validation "$work/contract-validation.json"
 Step delivery-audit {& (Join-Path $PSScriptRoot 'check-b03-delivery.ps1') -ReportFile "$work/delivery-audit.json"}
 Save-Report delivery-audit "$work/delivery-audit.json"
 $result.normalPackageBoundary='PASSED';$result.sameArtifactsAcrossBatch=$true
 $failed=$false
}finally{
 $current=@{};Get-ChildItem Env: | ForEach-Object {$current[$_.Name]=$_.Value}
 $changed=@(@($current.Keys)+@($original.Keys) | Sort-Object -Unique | Where-Object {$current[$_] -cne $original[$_]})
 $busy=@(@(50051,18091,18092,5173) | Where-Object {Test-Port $_})
 $result.environmentRestored=$changed.Count -eq 0;$result.changedEnvironmentNamesCount=$changed.Count;$result.ownedPortsReleased=$busy.Count -eq 0
 $result.defaultJavaUnchanged=(& java -version 2>&1 | Out-String).Trim() -ceq $defaultJava
 $result.mainBAndAClean=(@(& git -C ../zj-market status --porcelain).Count -eq 0 -and @(& git -C ../group-buy-market status --porcelain).Count -eq 0)
 $result.branch=(& git branch --show-current);$result.head=(& git rev-parse HEAD)
 $result.finishedAt=[DateTimeOffset]::UtcNow.ToString('o')
 $result.status=if(-not $failed -and $result.environmentRestored -and $result.ownedPortsReleased -and $result.defaultJavaUnchanged -and $result.mainBAndAClean){'PASSED'}else{'FAILED'}
 $result | ConvertTo-Json -Depth 8 | Set-Content "$work/report.json" -Encoding utf8
 [IO.File]::WriteAllText("$work/progress.txt",$result.status)
 Pop-Location
 if($changed.Count -or $busy.Count){throw 'Caller environment/owned ports not restored; see metadata-only report.'}
}
if($result.status -ne 'PASSED'){throw 'B-04.6 joint acceptance failed.'}
Write-Host "B-04 joint acceptance: PASSED. Report: $work/report.json"
