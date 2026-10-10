[CmdletBinding()]
param([string]$JavaHome='', [string]$AJavaHome='D:/Dev_tools/2.environment/jdk/jdk8', [string]$RunName='', [switch]$SkipBuild)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome
if($PSVersionTable.PSVersion.Major -lt 7){throw 'Joint acceptance requires PowerShell 7.'}
if(-not $RunName){$RunName='b036-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($RunName -notmatch '^[A-Za-z0-9-]+$'){throw 'Use a simple unique run name.'}
$work=Join-Path $root "target/b03-acceptance/$RunName"
if(Test-Path -LiteralPath $work){throw 'Use a new batch; previous evidence is retained.'}
New-Item -ItemType Directory -Path $work | Out-Null
$started=[DateTime]::UtcNow
$original=@{};Get-ChildItem Env: | ForEach-Object {$original[$_.Name]=$_.Value}
$defaultJava=(& java -version 2>&1 | Out-String).Trim()
$result=[ordered]@{stage='B-03.6';status='RUNNING';runName=$RunName;java=$jdk.Home;steps=@();evidence=@{};artifacts=@{};paymentEnabled=$false}
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
 foreach($artifact in @('zj-market-app/target/zj-market-app-exec.jar','zj-market-app/target/zj-market-app.jar','zj-market-verification/target/zj-market-verification.jar','frontend/package-lock.json')){$result.artifacts[$artifact]=(Get-FileHash -LiteralPath $artifact).Hash}
 Step normal-runtime {
  & (Join-Path $root 'scripts/start-b.ps1') -JavaHome $jdk.Home -SkipBuild -ApplicationArguments @('--spring.main.web-application-type=none','--b.identity.enabled=false','--b.product.enabled=false','--b.inventory.enabled=false','--b.order.enabled=false','--b.trade.enabled=false','--b.trial.enabled=false','--b.sync.enabled=false','--b.infrastructure.database.enabled=false','--b.infrastructure.rpc.enabled=false','--b.infrastructure.mq.enabled=false')
 }
 if(-not([IO.File]::ReadAllText("$work/normal-runtime.log") -match 'using Java 21\.')){throw 'Ordinary runtime did not prove target JDK.'}
 Step development-schema {& (Join-Path $root 'scripts/provision-b-database.ps1') -JavaHome $jdk.Home -SkipBuild}
 Copy-Item target/database/migrate.txt "$work/development-migrate.txt";Save-Report development-permissions 'target/database/verify.txt'
 Step test-schema {& (Join-Path $root 'scripts/provision-b-database.ps1') -TestDatabase -JavaHome $jdk.Home -SkipBuild}
 Copy-Item target/database/migrate.txt "$work/test-migrate.txt";Save-Report test-permissions 'target/database/verify.txt'
 Step b02-regression {& (Join-Path $PSScriptRoot 'run-b02-acceptance.ps1') -JavaHome $jdk.Home -AJavaHome $AJavaHome -RunName "$RunName-b02" -SkipBuild -ScopedSyncBrowser}
 Save-Report b02-regression "target/acceptance/$RunName-b02/report.json"
 foreach($phase in @('inventory','orders','trades','closes','joint-faults')){
  Step $phase {& (Join-Path $PSScriptRoot "run-b03-$phase.ps1") -JavaHome $jdk.Home -SkipBuild}
  $file=if($phase -eq 'joint-faults'){"target/$phase/verify.json"}else{"target/$phase/verify.txt"}
  Save-Report $phase $file
 }
 Step real-a {& (Join-Path $PSScriptRoot 'run-b03-readiness.ps1') -JavaHome $jdk.Home -AJavaHome $AJavaHome -RunName "$RunName-live" -WithJointFaults -SkipBuild}
 $live="target/b03-readiness/$RunName-live"
 foreach($item in @(@('real-a','report.json'),@('real-a-reserve-restart','trade-recovery.json'),@('real-a-close-restart','close-recovery.json'),@('real-a-close','close-recover.txt'),@('real-a-outage','close-outage.txt'),@('real-a-outage-recovery','close-outage-recovery.json'),@('real-a-outage-processes','a-outage-processes.json'))){Save-Report $item[0] "$live/$($item[1])"}
 Copy-Item "$live/provenance.txt" "$work/real-a-provenance.txt"
 Step inventory-browser {& (Join-Path $PSScriptRoot 'run-b03-inventory-browser.ps1') -JavaHome $jdk.Home -SkipBuild -SkipBackendChecks -InventoryOnly}
 Save-Report inventory-browser 'target/inventory/browser.json'
 Step order-team-close-browser {& (Join-Path $PSScriptRoot 'run-b03-orders-browser.ps1') -JavaHome $jdk.Home -SkipBuild -SkipBackendChecks -OrdersOnly -WithClose}
 foreach($phase in @('orders','trades','closes')){Save-Report "$phase-browser" "target/$phase/browser.json"}
 $entries=& (Join-Path $jdk.Home 'bin/jar.exe') tf zj-market-app/target/zj-market-app-exec.jar
 if($LASTEXITCODE -ne 0 -or @($entries | Where-Object {$_ -match 'verification|flyway'}).Count){throw 'Ordinary package contains verification/migration dependency.'}
 foreach($entry in $result.artifacts.GetEnumerator()){if((Get-FileHash -LiteralPath $entry.Key).Hash -ne $entry.Value){throw 'Artifacts changed during joint acceptance.'}}
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
 $result.finishedAt=[DateTimeOffset]::UtcNow.ToString('o')
 $result.status=if(-not $failed -and $result.environmentRestored -and $result.ownedPortsReleased -and $result.defaultJavaUnchanged){'PASSED'}else{'FAILED'}
 $result | ConvertTo-Json -Depth 8 | Set-Content "$work/report.json" -Encoding utf8
 [IO.File]::WriteAllText("$work/progress.txt",$result.status)
 Pop-Location
 if($changed.Count -or $busy.Count){throw 'Caller environment/owned ports not restored; see metadata-only report.'}
}
if($result.status -ne 'PASSED'){throw 'B-03.6 joint acceptance failed.'}
Write-Host "B-03 joint acceptance: PASSED. Report: $work/report.json"
