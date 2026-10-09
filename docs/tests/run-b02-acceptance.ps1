[CmdletBinding()]
param([string]$JavaHome='', [string]$AJavaHome='D:/Dev_tools/2.environment/jdk/jdk8', [string]$RunName='', [switch]$SkipBuild)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome
if(-not $RunName){$RunName='b026-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($RunName -notmatch '^[a-zA-Z0-9-]+$'){throw 'Use a simple new run name'}
$work=Join-Path $root "target/acceptance/$RunName"
if(Test-Path $work){throw 'Use a new run directory; previous evidence is immutable'}
New-Item -ItemType Directory -Path $work | Out-Null
$original=@{};Get-ChildItem Env: | ForEach-Object {$original[$_.Name]=$_.Value}
$result=[ordered]@{stage='B-02.6';status='RUNNING';runName=$RunName;java=$jdk.Home;steps=@();evidence=@{};artifacts=@{}}
function Test-OwnedPort([int]$port){$client=[Net.Sockets.TcpClient]::new();try{return $client.ConnectAsync('127.0.0.1',$port).Wait(500)}catch{return $false}finally{$client.Dispose()}}
function Step([string]$name,[scriptblock]$action){
 [IO.File]::WriteAllText("$work/progress.txt",$name)
 & $action *> "$work/$name.log"
 $script:result.steps+=@($name)
}
function Require-TextReport([string]$name,[string]$path){
 if(-not(Test-Path $path) -or -not([IO.File]::ReadAllText($path).Contains('status=PASSED'))){throw "Missing passing report: $name"}
 $script:result.evidence[$name]=$path
}
Push-Location $root
$failed=$true
try{
 foreach($port in @(50051,18091,18092,5173)){if(Test-OwnedPort $port){throw "Acceptance-owned port $port is occupied; no unrelated process will be stopped"}}
 foreach($file in @('.local/database.credentials.xml','.local/b02-test-database.credentials.xml')){if(-not(Test-Path $file)){throw 'Existing separate B database credential records required'}}
 if(-not $SkipBuild){Step build {Invoke-BMaven -JavaHome $jdk.Home -Arguments @('-B','package')}}
 Step dependencies {Invoke-BMaven -JavaHome $jdk.Home -Arguments @('-B','dependency:tree','-Dverbose',"-DoutputFile=target/b026-dependencies.txt")}
 foreach($scope in @('development','b02-test')){
  $credential=Join-Path $root $(if($scope -eq 'development'){'.local/database.credentials.xml'}else{'.local/b02-test-database.credentials.xml'})
  foreach($mode in @('migrate','verify')){
   Step "$scope-$mode" {& (Join-Path $root 'scripts/database.ps1') -Mode $mode -CredentialFile $credential -JavaHome $jdk.Home -SkipBuild}
   $copy="$work/$scope-$mode.txt";Copy-Item "target/database/$mode.txt" $copy;Require-TextReport "$scope-$mode" $copy
  }
 }
 # All operations use isolated learning fixtures; shared services remain running.
 Step synchronization {& (Join-Path $PSScriptRoot 'run-b02-sync.ps1') -JavaHome $jdk.Home -AJavaHome $AJavaHome -RunName "$RunName-sync" -SkipBuild -AckRestart -Browser}
 $sync=Join-Path $root "target/sync/$RunName-sync"
 Require-TextReport 'sync-core' "$sync/verify.txt";Require-TextReport 'commit-before-ACK-restart' "$sync/ack-recovery.txt"
 foreach($kind in @('identity','products','sync')){Copy-Item "target/$kind/browser.txt" "$work/$kind-browser.txt";Require-TextReport "$kind-browser" "$work/$kind-browser.txt"}
 Step trial {& (Join-Path $PSScriptRoot 'run-b02-trial.ps1') -JavaHome $jdk.Home -AJavaHome $AJavaHome -RunName "$RunName-trial" -SkipBuild -Browser}
 $trial=Join-Path $root "target/trial/$RunName-trial"
 foreach($name in @('verify','browser','browser-offline','offline')){Require-TextReport "trial-$name" "$trial/$name.txt"}
 Step middleware-baseline {& (Join-Path $PSScriptRoot 'run-b01-environment.ps1') -JavaHome $jdk.Home -AJavaHome $AJavaHome -RunName "$RunName-baseline" -SkipBuild}
 $probe=Join-Path $root "target/environment-probe/$RunName-baseline/report.json";$baseline=Get-Content $probe -Raw | ConvertFrom-Json
 if($baseline.status -ne 'PASSED'){throw 'Fixed middleware baseline did not pass'};$result.evidence['middleware-baseline']=$probe
 $entries=& (Join-Path $jdk.Home 'bin/jar.exe') tf zj-market-app/target/zj-market-app-exec.jar
 if($LASTEXITCODE -ne 0 -or @($entries | Where-Object {$_ -match 'verification|flyway'}).Count -ne 0){throw 'Ordinary package boundary failed'}
 [IO.File]::WriteAllLines("$work/package-boundary.txt",@('normal-app-verification/Flyway=ABSENT','status=PASSED'));Require-TextReport 'normal-package' "$work/package-boundary.txt"
 $contract=Get-Content (Join-Path $root 'docs/b02-http-api.json') -Raw | ConvertFrom-Json -AsHashtable
 $operations=@();foreach($path in $contract.paths.Values){foreach($method in @('get','post','put','patch','delete')){if($path.ContainsKey($method)){$operations+=@($path[$method])}}}
 if($operations.Count -ne 18 -or @($operations | Where-Object {$_['x-implementation-status'] -notlike 'implemented-*'}).Count -ne 0){throw 'HTTP implementation inventory mismatch'}
 $refs=[regex]::Matches(([IO.File]::ReadAllText((Join-Path $root 'docs/b02-http-api.json'))),'"\$ref"\s*:\s*"([^"]+)"')
 foreach($ref in $refs){$pointer=$ref.Groups[1].Value;if(-not $pointer.StartsWith('#/')){throw 'Unexpected external HTTP schema reference'};$value=$contract;foreach($part in $pointer.Substring(2).Split('/')){$key=$part.Replace('~1','/').Replace('~0','~');if(-not $value.ContainsKey($key)){throw 'Invalid local HTTP reference'};$value=$value[$key]}}
 [IO.File]::WriteAllLines("$work/http-contract.txt",@('operations=18','implemented=18',"local-refs-valid=$($refs.Count)",'status=PASSED'));Require-TextReport 'http-contract' "$work/http-contract.txt"
 foreach($file in @('zj-market-app/target/zj-market-app-exec.jar','zj-market-verification/target/zj-market-verification.jar','frontend/package-lock.json')){$result.artifacts[$file]=(Get-FileHash $file -Algorithm SHA256).Hash}
 $failed=$false
}finally{
 $current=@{};Get-ChildItem Env: | ForEach-Object {$current[$_.Name]=$_.Value}
 $changed=@(@($current.Keys)+@($original.Keys) | Sort-Object -Unique | Where-Object {$current[$_] -cne $original[$_]})
 $busy=@(@(50051,18091,18092,5173) | Where-Object {Test-OwnedPort $_})
 $result.environmentRestored=$changed.Count -eq 0;$result.changedEnvironmentNamesCount=$changed.Count;$result.ownedPortsReleased=$busy.Count -eq 0
 & java -version 2> "$work/default-java.txt"
 $result.status=if(-not $failed -and $changed.Count -eq 0 -and $busy.Count -eq 0){'PASSED'}else{'FAILED'}
 $result | ConvertTo-Json -Depth 8 | Set-Content "$work/report.json" -Encoding utf8
 [IO.File]::WriteAllText("$work/progress.txt",$result.status)
 Pop-Location
 if($changed.Count -ne 0 -or $busy.Count -ne 0){throw 'Caller environment or owned port restoration failed; see metadata-only report'}
}
if($result.status -ne 'PASSED'){throw 'B-02 acceptance failed'}
Write-Host "B-02 joint acceptance: PASSED. Report: $work/report.json"
