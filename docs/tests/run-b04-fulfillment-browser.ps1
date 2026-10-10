[CmdletBinding()]
param([string]$JavaHome='', [string]$RunName='', [switch]$SkipBuild)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome
function Test-Port([int]$port){$c=[Net.Sockets.TcpClient]::new();try{return $c.ConnectAsync('127.0.0.1',$port).Wait(500)}catch{return $false}finally{$c.Dispose()}}
foreach($port in @(18092,5173)){if(Test-Port $port){throw "Port $port occupied; refusing to stop unrelated processes"}}
if(-not $RunName){$RunName='b045-browser-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($RunName -notmatch '^[a-zA-Z0-9-]+$'){throw 'Invalid run name'}
$work=Join-Path $root "target/payments/$RunName"
if(Test-Path -LiteralPath $work){throw 'Use a fresh run name'}
$backend=$null;$frontend=$null
$previous=@{};foreach($name in @('B_PAYMENT_BROWSER_WORK','B_WEB_API_TARGET')){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
Push-Location $root
try{
 if(-not $SkipBuild){Invoke-BMaven -JavaHome $jdk.Home -Arguments @('-B','package')}
 & npm run build --prefix frontend *> target/b045-browser-frontend-build.log
 if($LASTEXITCODE -ne 0){throw 'Frontend build failed'}
 if(-not(Test-Path target/b02-browser-runtime/node_modules/playwright)){& npm install --prefix target/b02-browser-runtime playwright@1.64.0 --registry=https://registry.npmjs.org --fetch-timeout=20000 --fetch-retries=1 *> target/b045-browser-install.log;if($LASTEXITCODE -ne 0){throw 'Browser verification dependency unavailable'}}
 $ps=(Get-Process -Id $PID).Path;$node=(Get-Command node).Source
 $backend=Start-Process -FilePath $ps -WindowStyle Hidden -PassThru -ArgumentList @('-NoProfile','-File',(Join-Path $PSScriptRoot 'run-b04-payments.ps1'),'-JavaHome',('"'+$jdk.Home+'"'),'-RunName',$RunName,'-Browser','-SettlementBrowser','-SkipBuild') -RedirectStandardOutput target/b045-browser-server.log -RedirectStandardError target/b045-browser-server.err.log
 Restore-BEnvironmentVariable B_WEB_API_TARGET 'http://127.0.0.1:18092'
 $frontend=Start-Process -FilePath $node -WindowStyle Hidden -PassThru -WorkingDirectory (Join-Path $root 'frontend') -ArgumentList @((Join-Path $root 'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--strictPort') -RedirectStandardOutput target/b045-browser-vite.log -RedirectStandardError target/b045-browser-vite.err.log
 $deadline=[DateTime]::UtcNow.AddSeconds(60)
 while(-not(Test-Port 18092) -or -not(Test-Port 5173) -or -not(Test-Path "$work/browser-ready.txt")){if($backend.HasExited -or $frontend.HasExited -or [DateTime]::UtcNow -gt $deadline){throw 'Owned payment browser fixtures failed to start'};Start-Sleep -Milliseconds 200}
 Restore-BEnvironmentVariable B_PAYMENT_BROWSER_WORK $work
 & $node (Join-Path $PSScriptRoot 'b04-fulfillment-browser.mjs') *> "$work/browser.log"
 if($LASTEXITCODE -ne 0){throw 'Payment browser verification failed; inspect ignored report'}
 Get-Content "$work/browser.json"
}finally{
 if(Test-Path $work){[IO.File]::WriteAllText((Join-Path $work 'browser-stop.txt'),'STOP')}
 if($backend){if(-not $backend.WaitForExit(10000)){Get-CimInstance Win32_Process -Filter "ParentProcessId=$($backend.Id)" | Where-Object {$_.Name -eq 'java.exe' -and $_.CommandLine -like '*zj-market-verification.jar*'} | ForEach-Object {Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue};Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue}}
 if($frontend){Stop-Process -Id $frontend.Id -ErrorAction SilentlyContinue}
 if(Test-Path "$work/browser-private.json"){Remove-Item -LiteralPath "$work/browser-private.json"}
 foreach($name in $previous.Keys){Restore-BEnvironmentVariable $name $previous[$name]}
 Pop-Location
}
