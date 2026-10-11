[CmdletBinding()]
param([string]$JavaHome='C:/Program Files/Java/jdk-21',[Parameter(Mandatory)][string]$RunName,[switch]$SkipBuild)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
if($RunName -notmatch '^b056-[A-Za-z0-9-]+$'){throw 'Use a fresh B056 run name'}
$work=Join-Path $root "target/b05-joint/$RunName"
if(Test-Path $work){throw 'Use a new joint batch; never overwrite evidence'}
New-Item -ItemType Directory -Path $work|Out-Null
# B055 fixture prefix is retained because the existing isolated runner enforces it.
$prefix="b055-$RunName"
$report=[ordered]@{status='RUNNING';runName=$RunName;prefix=$prefix;phases=@()}
function Phase([string]$name,[scriptblock]$action){
 & $action *> "$work/$name.log"
 if(-not $?){throw "Joint phase $name failed"}
 $report.phases+=@{name=$name;status='PASSED'}
 $report|ConvertTo-Json -Depth 8|Set-Content "$work/progress.json"
}
Push-Location $root
try{
 if(-not $SkipBuild){Phase build {Invoke-BMaven -JavaHome $JavaHome -Arguments @('-B','package')}}
 $report.verificationJarSha256=(Get-FileHash zj-market-verification/target/zj-market-verification.jar).Hash
 $report.applicationJarSha256=(Get-FileHash zj-market-app/target/zj-market-app-exec.jar).Hash
 Phase reconciliation {./docs/tests/run-b05-reconciliation.ps1 -JavaHome $JavaHome -RunName "$prefix-reconciliation" -SkipBuild}
 Phase refund {./docs/tests/run-b05-refund-release.ps1 -JavaHome $JavaHome -RunName "$prefix-sql" -SkipBuild}
 Phase browser {./docs/tests/run-b05-refund-browser.ps1 -JavaHome $JavaHome -RunName "$prefix-browser" -SqlBatch "$prefix-sql"}
 Phase actual-none {./docs/tests/run-b03-readiness.ps1 -JavaHome $JavaHome -WithReconciliation -ReconciliationPaymentCase NONE -AProviderRpcPort 50052 -AProviderHttpPort 18092 -RunName "$prefix-none" -SkipBuild}
 Phase actual-partial {./docs/tests/run-b03-readiness.ps1 -JavaHome $JavaHome -WithRefundRelease -AProviderRpcPort 50052 -AProviderHttpPort 18092 -RunName "$prefix-partial" -SkipBuild}
 Phase actual-completed {./docs/tests/run-b03-readiness.ps1 -JavaHome $JavaHome -WithReconciliationCompletion -AProviderRpcPort 50052 -AProviderHttpPort 18092 -RunName "$prefix-completed" -SkipBuild}
 Phase regressions {./docs/tests/run-b05-refund-release-regressions.ps1 -JavaHome $JavaHome -Prefix $prefix}
 if((Get-FileHash zj-market-verification/target/zj-market-verification.jar).Hash -ne $report.verificationJarSha256){throw 'Final verification package changed'}
 if((Get-FileHash zj-market-app/target/zj-market-app-exec.jar).Hash -ne $report.applicationJarSha256){throw 'Final application package changed'}
 $report.status='PASSED'
}catch{$report.status='FAILED';$report.error=$_.Exception.Message;throw}
finally{$report|ConvertTo-Json -Depth 8|Set-Content "$work/report.json";Pop-Location}
Write-Host "B-05.6 same-package joint acceptance: $($report.status)"
