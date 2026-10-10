[CmdletBinding()]
param([string]$JavaHome='', [switch]$SkipBuild,[switch]$SkipBackendChecks,[switch]$InventoryOnly, [string]$BrowserExecutable='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome
if($PSVersionTable.PSVersion.Major -lt 7){throw 'Browser acceptance uses PowerShell 7.'}
if(-not(Test-Path -LiteralPath $BrowserExecutable)){throw 'Supply installed browser executable.'}
function Test-Port([int]$Port){$client=[Net.Sockets.TcpClient]::new();try{return $client.ConnectAsync('127.0.0.1',$Port).Wait(500)}catch{return $false}finally{$client.Dispose()}}
foreach($port in @(18092,5173)){if(Test-Port $port){throw "Port $port is occupied; acceptance will not stop unrelated processes."}}
$names=@('B_IDENTITY_ORIGIN','B_IDENTITY_SECURE_COOKIES','B_IDENTITY_KEY_ID','B_IDENTITY_PRIVATE_KEY_FILE','B_IDENTITY_PUBLIC_KEY_FILE','B_OPERATOR_LOGIN_NAME','B_OPERATOR_PASSWORD','B_OPERATOR_DISPLAY_NAME','B_BROWSER_OPERATOR_LOGIN_NAME','B_BROWSER_OPERATOR_PASSWORD','B_BROWSER_EXECUTABLE','B_WEB_API_TARGET','B_PRODUCT_EVENT_PRODUCER','B_PRODUCT_EVENT_SOURCE','B_PRODUCT_EVENT_CHANNEL','B_INVENTORY_ENABLED','B_BROWSER_OTHER_LOGIN_NAME','B_BROWSER_OTHER_PASSWORD')
$previous=@{};foreach($name in $names){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
$backend=$null;$frontend=$null
$browserReport=Join-Path $root 'target/inventory/browser.txt'
New-Item -ItemType Directory -Path (Split-Path $browserReport -Parent) -Force | Out-Null
[IO.File]::WriteAllText($browserReport,'status=RUNNING')
Push-Location $root
try{
    if(-not $SkipBackendChecks){
    & (Join-Path $PSScriptRoot 'run-b02-identity.ps1') -JavaHome $JavaHome -SkipBuild:$SkipBuild
    & (Join-Path $PSScriptRoot 'run-b03-inventory.ps1') -JavaHome $JavaHome -SkipBuild
    }
    Restore-BEnvironmentVariable B_INVENTORY_ENABLED true
    Restore-BEnvironmentVariable B_PRODUCT_EVENT_PRODUCER 'zj-market'
    Restore-BEnvironmentVariable B_PRODUCT_EVENT_SOURCE 's01'
    Restore-BEnvironmentVariable B_PRODUCT_EVENT_CHANNEL 'c01'
    Restore-BEnvironmentVariable B_IDENTITY_ORIGIN 'http://127.0.0.1:5173'
    Restore-BEnvironmentVariable B_IDENTITY_SECURE_COOKIES false
    Restore-BEnvironmentVariable B_IDENTITY_KEY_ID b02-test
    Restore-BEnvironmentVariable B_IDENTITY_PRIVATE_KEY_FILE (Join-Path $root '.local/b02-test-keys/private.pem')
    Restore-BEnvironmentVariable B_IDENTITY_PUBLIC_KEY_FILE (Join-Path $root '.local/b02-test-keys/public.pem')
    Restore-BEnvironmentVariable B_OPERATOR_LOGIN_NAME ('browser_op_'+[guid]::NewGuid().ToString('N').Substring(0,12))
    Restore-BEnvironmentVariable B_OPERATOR_PASSWORD ([guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N'))
    Restore-BEnvironmentVariable B_OPERATOR_DISPLAY_NAME 'Browser operator'
    & (Join-Path $root 'scripts/identity.ps1') -Mode init-operator -CredentialFile (Join-Path $root '.local/b02-test-database.credentials.xml') -JavaHome $JavaHome -SkipBuild
    Restore-BEnvironmentVariable B_BROWSER_OPERATOR_LOGIN_NAME $env:B_OPERATOR_LOGIN_NAME
    Restore-BEnvironmentVariable B_BROWSER_OPERATOR_PASSWORD $env:B_OPERATOR_PASSWORD
    $firstCredential=[Management.Automation.PSCredential]::new($env:B_BROWSER_OPERATOR_LOGIN_NAME,(ConvertTo-SecureString $env:B_BROWSER_OPERATOR_PASSWORD -AsPlainText -Force))
    Restore-BEnvironmentVariable B_OPERATOR_LOGIN_NAME ('browser_other_'+[guid]::NewGuid().ToString('N').Substring(0,12))
    Restore-BEnvironmentVariable B_OPERATOR_PASSWORD ([guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N'))
    & (Join-Path $root 'scripts/identity.ps1') -Mode init-operator -CredentialFile (Join-Path $root '.local/b02-test-database.credentials.xml') -JavaHome $JavaHome -SkipBuild
    Restore-BEnvironmentVariable B_BROWSER_OTHER_LOGIN_NAME $env:B_OPERATOR_LOGIN_NAME
    Restore-BEnvironmentVariable B_BROWSER_OTHER_PASSWORD $env:B_OPERATOR_PASSWORD
    @{Operator=$firstCredential;Other=[Management.Automation.PSCredential]::new($env:B_BROWSER_OTHER_LOGIN_NAME,(ConvertTo-SecureString $env:B_BROWSER_OTHER_PASSWORD -AsPlainText -Force))} | Export-Clixml -LiteralPath (Join-Path $root '.local/b03-inventory-browser.credentials.xml')
    foreach($name in @('B_OPERATOR_LOGIN_NAME','B_OPERATOR_PASSWORD','B_OPERATOR_DISPLAY_NAME')){Restore-BEnvironmentVariable $name $null}
    Restore-BEnvironmentVariable B_BROWSER_EXECUTABLE $BrowserExecutable
    Restore-BEnvironmentVariable B_WEB_API_TARGET 'http://127.0.0.1:18092'
    & npm ci --prefix frontend --offline *> target/b02-frontend-ci.txt
    if($LASTEXITCODE -ne 0){throw 'Frontend dependency installation failed.'}
    & npm run build --prefix frontend *> target/b02-frontend-build.txt
    if($LASTEXITCODE -ne 0){throw 'Frontend type/build verification failed.'}
    if(-not(Test-Path target/b02-browser-runtime/node_modules/playwright)){
        & npm install --prefix target/b02-browser-runtime playwright@1.64.0 --registry=https://registry.npmjs.org --fetch-timeout=20000 --fetch-retries=1 *> target/b02-browser-install.txt
        if($LASTEXITCODE -ne 0){throw 'Browser verification dependency installation failed.'}
    }
    $ps=(Get-Process -Id $PID).Path
    $backend=Start-Process -FilePath $ps -ArgumentList @('-NoProfile','-File',(Join-Path $root 'scripts/start-products.ps1'),'-TestDatabase','-SkipBuild','-JavaHome',('"'+$jdk.Home+'"')) -WindowStyle Hidden -PassThru -RedirectStandardOutput target/b023-browser-backend.txt -RedirectStandardError target/b023-browser-backend.err.txt
    $node=(Get-Command node).Source
    $frontend=Start-Process -FilePath $node -ArgumentList @((Join-Path $root 'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1') -WorkingDirectory (Join-Path $root 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput target/b023-browser-frontend.txt -RedirectStandardError target/b023-browser-frontend.err.txt
    $deadline=[DateTime]::UtcNow.AddSeconds(30)
    while(-not(Test-Port 18092) -or -not(Test-Port 5173)){
        if($backend.HasExited -or $frontend.HasExited -or [DateTime]::UtcNow -gt $deadline){throw 'B test web startup failed; inspect ignored target logs.'}
        Start-Sleep -Milliseconds 200
    }
    if(-not $InventoryOnly){
    & $node (Join-Path $PSScriptRoot 'b02-browser.mjs') *> target/b02-browser-run.txt
    if($LASTEXITCODE -ne 0){throw 'B browser identity verification failed; inspect ignored target log.'}
    Get-Content target/identity/browser.txt
    & $node (Join-Path $PSScriptRoot 'b02-products-browser.mjs') *> target/b023-browser-run.txt
    if($LASTEXITCODE -ne 0){throw 'B product browser verification failed; inspect ignored target log.'}
    Get-Content target/products/browser.txt
    }
    & $node (Join-Path $PSScriptRoot 'b03-inventory-browser.mjs') *> target/b032-browser-run.log
    if($LASTEXITCODE -ne 0){throw 'Inventory browser acceptance failed; inspect ignored target log.'}
    [IO.File]::WriteAllText($browserReport,'status=PASSED')
    Get-Content target/inventory/browser.json
}catch{[IO.File]::WriteAllText($browserReport,'status=FAILED');throw}finally{
    if($backend){
        # Stop only children of the process launched by this invocation.
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$($backend.Id)" | Where-Object { $_.Name -eq 'java.exe' -and $_.CommandLine -like '*zj-market-app-exec.jar*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
        Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
    }
    if($frontend){Stop-Process -Id $frontend.Id -ErrorAction SilentlyContinue}
    foreach($name in $names){Restore-BEnvironmentVariable $name $previous[$name]}
    Pop-Location
}
