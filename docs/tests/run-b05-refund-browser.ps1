[CmdletBinding()]
param([string]$JavaHome='C:/Program Files/Java/jdk-21',[Parameter(Mandatory)][string]$SqlBatch,[string]$RunName='')
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome
if($SqlBatch -notmatch '^b055-[A-Za-z0-9-]+$'){throw 'Use a B055 SQL acceptance fixture'}
if(-not $RunName){$RunName='b055-browser-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($RunName -notmatch '^[A-Za-z0-9-]+$'){throw 'Invalid fresh run name'}
$work=Join-Path $root "target/refund/$RunName"
if(Test-Path $work){throw 'Use a fresh browser batch'}
foreach($port in @(18092,5173)){if(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue){throw "Port $port occupied; refusing to stop unrelated processes"}}
$fixture=Join-Path $root "target/refund/$SqlBatch/browser-private.json"
if(-not(Test-Path $fixture)){throw 'Owned SQL fixtures missing'}
New-Item -ItemType Directory -Path $work|Out-Null
Copy-Item -LiteralPath $fixture -Destination "$work/browser-private.json"
$names=@('B_DATABASE_ENABLED','B_DATABASE_URL','B_DATABASE_USERNAME','B_DATABASE_PASSWORD','B_DATABASE_SCOPE','B_IDENTITY_ORIGIN','B_IDENTITY_SECURE_COOKIES','B_IDENTITY_KEY_ID','B_IDENTITY_PRIVATE_KEY_FILE','B_IDENTITY_PUBLIC_KEY_FILE','B_PRODUCT_EVENT_PRODUCER','B_PRODUCT_EVENT_SOURCE','B_PRODUCT_EVENT_CHANNEL','B_PAYMENT_WORK','B_PAYMENT_BROWSER_WORK','B_WEB_API_TARGET')
$previous=@{};foreach($name in $names){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
$backend=$null;$frontend=$null;$report=[ordered]@{status='RUNNING';sqlBatch=$SqlBatch}
Push-Location $root
try{
 if(-not(Test-Path 'target/b02-browser-runtime/node_modules/playwright')){& npm install --prefix target/b02-browser-runtime playwright@1.64.0 --registry=https://registry.npmjs.org --fetch-timeout=20000 --fetch-retries=1 *> "$work/browser-install.log";if($LASTEXITCODE -ne 0){throw 'Browser verification dependency unavailable'}}
 $c=Import-Clixml .local/b02-test-database.credentials.xml
 Restore-BEnvironmentVariable B_DATABASE_ENABLED true
 Restore-BEnvironmentVariable B_DATABASE_URL $c.Url
 Restore-BEnvironmentVariable B_DATABASE_USERNAME $c.Runtime.UserName
 Restore-BEnvironmentVariable B_DATABASE_PASSWORD $c.Runtime.GetNetworkCredential().Password
 Restore-BEnvironmentVariable B_DATABASE_SCOPE $c.Scope
 Restore-BEnvironmentVariable B_IDENTITY_ORIGIN 'http://127.0.0.1:5173'
 Restore-BEnvironmentVariable B_IDENTITY_SECURE_COOKIES false
 Restore-BEnvironmentVariable B_IDENTITY_KEY_ID b02-test
 Restore-BEnvironmentVariable B_IDENTITY_PRIVATE_KEY_FILE "$root/.local/b02-test-keys/private.pem"
 Restore-BEnvironmentVariable B_IDENTITY_PUBLIC_KEY_FILE "$root/.local/b02-test-keys/public.pem"
 Restore-BEnvironmentVariable B_PRODUCT_EVENT_PRODUCER zj-market
 Restore-BEnvironmentVariable B_PRODUCT_EVENT_SOURCE s01
 Restore-BEnvironmentVariable B_PRODUCT_EVENT_CHANNEL c01
 Restore-BEnvironmentVariable B_PAYMENT_WORK $work
 Restore-BEnvironmentVariable B_PAYMENT_BROWSER_WORK $work
 Restore-BEnvironmentVariable B_WEB_API_TARGET 'http://127.0.0.1:18092'
 $jar=Join-Path $root 'zj-market-verification/target/zj-market-verification.jar'
 $report.verificationJarSha256=(Get-FileHash $jar).Hash
 $node=(Get-Command node).Source
 $backend=Start-Process -FilePath $jdk.Java -WindowStyle Hidden -PassThru -WorkingDirectory $root -ArgumentList @('-jar',$jar,'--refund-browser') -RedirectStandardOutput "$work/server.log" -RedirectStandardError "$work/server.err.log"
 $frontend=Start-Process -FilePath $node -WindowStyle Hidden -PassThru -WorkingDirectory "$root/frontend" -ArgumentList @("$root/frontend/node_modules/vite/bin/vite.js",'--host','127.0.0.1','--strictPort') -RedirectStandardOutput "$work/vite.log" -RedirectStandardError "$work/vite.err.log"
 $deadline=[DateTime]::UtcNow.AddSeconds(50)
 while(-not(Test-Path "$work/browser-ready.txt") -or -not(Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue)){if($backend.HasExited -or $frontend.HasExited -or [DateTime]::UtcNow -gt $deadline){throw 'Owned refund browser server failed to start'};Start-Sleep -Milliseconds 200}
 & $node docs/tests/b05-refund-browser.mjs *> "$work/browser.log"
 if($LASTEXITCODE -ne 0){throw 'Refund browser acceptance failed'}
 $report.status='PASSED'
}catch{$report.status='FAILED';$report.error=$_.Exception.Message;throw}
finally{
 [IO.File]::WriteAllText("$work/browser-stop.txt",'STOP')
 if($backend){if(-not $backend.WaitForExit(10000)){Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue}}
 if($frontend){Stop-Process -Id $frontend.Id -ErrorAction SilentlyContinue}
 if(Test-Path "$work/browser-private.json"){Remove-Item -LiteralPath "$work/browser-private.json"}
 $report.ownedPortsReleased=(-not(Get-NetTCPConnection -LocalPort 18092,5173 -State Listen -ErrorAction SilentlyContinue))
 $report|ConvertTo-Json -Depth 5|Set-Content "$work/report.json"
 foreach($name in $names){Restore-BEnvironmentVariable $name $previous[$name]}
 Pop-Location
}
Write-Host "B-05.5 real HTTP/browser acceptance: $($report.status)"
