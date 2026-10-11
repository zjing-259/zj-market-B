[CmdletBinding()]
param([string]$JavaHome='C:/Program Files/Java/jdk-21',[string]$RunName='')
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome
if(-not $RunName){$RunName='b053-startup-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($RunName -notmatch '^[A-Za-z0-9-]+$'){throw 'Invalid fresh run name'}
$work=Join-Path $root "target/refund/$RunName"
if(Test-Path -LiteralPath $work){throw 'Use a fresh startup batch'}
New-Item -ItemType Directory -Path $work | Out-Null
$beforeJava=(& java -version 2>&1|Out-String)
$previous=@{};Get-ChildItem Env: | Where-Object {$_.Name -like 'B_*'} | ForEach-Object {$previous[$_.Name]=$_.Value}
$process=$null;$report=[ordered]@{status='RUNNING';scope='ordinary executable defaults with no B environment';applicationJarSha256=(Get-FileHash "$root/zj-market-app/target/zj-market-app-exec.jar").Hash}
try{
 foreach($name in $previous.Keys){[Environment]::SetEnvironmentVariable($name,$null,'Process')}
 $process=Start-Process -FilePath $jdk.Java -WindowStyle Hidden -PassThru -WorkingDirectory $root -ArgumentList @('-jar',"$root/zj-market-app/target/zj-market-app-exec.jar",'--server.port=0') -RedirectStandardOutput "$work/stdout.log" -RedirectStandardError "$work/stderr.log"
 $deadline=[DateTime]::UtcNow.AddSeconds(40);$started=$false
 while([DateTime]::UtcNow -lt $deadline){$process.Refresh();if($process.HasExited){throw 'Ordinary application exited before startup'};if((Get-Content "$work/stdout.log" -Raw -ErrorAction SilentlyContinue) -match 'Started ZjMarketApplication'){$started=$true;break};Start-Sleep -Milliseconds 250}
 if(-not $started){throw 'Ordinary startup timeout'}
 $logs=(Get-Content "$work/stdout.log" -Raw)+(Get-Content "$work/stderr.log" -Raw)
 if($logs -match 'HikariPool|HikariDataSource|Flyway|Refund recovery pending|Reconciliation recovery pending'){throw 'Default startup unexpectedly enabled external execution'}
 $report.status='PASSED';$report.started=$true;$report.noDatabaseOrRecoveryByDefault=$true
}catch{$report.status='FAILED';$report.error=$_.Exception.Message;throw}
finally{
 if($process){$process.Refresh();if(-not $process.HasExited){Stop-Process -Id $process.Id;[void]$process.WaitForExit(10000)};$report.ownedProcessStopped=$process.HasExited}
 foreach($name in $previous.Keys){[Environment]::SetEnvironmentVariable($name,$previous[$name],'Process')}
 $report.defaultJavaUnchanged=((& java -version 2>&1|Out-String) -eq $beforeJava)
 $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$work/report.json"
}
Write-Host "B-05.3 ordinary default startup: $($report.status)"
