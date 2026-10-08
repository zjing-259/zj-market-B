[CmdletBinding()]
param([string]$JavaHome='', [string]$AJavaHome='D:/Dev_tools/2.environment/jdk/jdk8', [string]$RunName='', [switch]$SkipBuild, [switch]$Browser, [switch]$AckRestart)
$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $projectRoot 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome;$java=$jdk.Java
$AProject=Join-Path (Split-Path $projectRoot -Parent) 'group-buy-market'
$localA=Join-Path $AProject 'docs/dev-ops/ab-v2/.local'
$aJar=Join-Path $AProject 'group-buy-market-app/target/group-buy-market-app.jar'
$bJar=Join-Path $projectRoot 'zj-market-verification/target/zj-market-verification.jar'
if(-not $RunName){$RunName='b024-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($RunName -notmatch '^[a-zA-Z0-9-]+$'){throw 'Invalid run name'}
$work=Join-Path $projectRoot "target/sync/$RunName"
if(Test-Path (Join-Path $work 'fixtures.json')){throw 'Use a new run name; persisted fixture manifest is immutable'}
New-Item -ItemType Directory -Path $work -Force | Out-Null
$previousEnvironment=@{};$provider=$null;$consumer=$null
function Set-ProbeEnvironment([string]$name, [AllowNull()]$value) {
    if (-not $previousEnvironment.ContainsKey($name)) {
        $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
    }
    Restore-BEnvironmentVariable -Name $name -Value $value
}
function Import-ProbeEnvironment([string]$path) {
    foreach ($line in Get-Content -LiteralPath $path) {
        if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { Set-ProbeEnvironment $Matches[1] $Matches[2] }
    }
}
function Test-ProbePort([int]$port) {
    $socket = [Net.Sockets.TcpClient]::new()
    try {
        $pending = $socket.BeginConnect('127.0.0.1', $port, $null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne(500)) { return $false }
        $socket.EndConnect($pending); return $true
    } catch { return $false } finally { $socket.Dispose() }
}
function Wait-ProbeProcess($process, [int]$seconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($seconds)
    while (-not $process.HasExited) {
        if ([DateTime]::UtcNow -ge $deadline) { throw 'Probe process exceeded its bounded timeout; see ignored logs.' }
        Start-Sleep -Milliseconds 300
        $process.Refresh()
    }
    $process.WaitForExit()
}

function Invoke-SyncPhase([string]$phase,[int]$expectedExit=0){
 $script:consumer=Start-Process -FilePath $java -WindowStyle Hidden -PassThru -WorkingDirectory $projectRoot -ArgumentList @('-jar',$bJar,'--sync',$phase) -RedirectStandardOutput "$work/$phase.stdout.log" -RedirectStandardError "$work/$phase.stderr.log"
 Wait-ProbeProcess $consumer 240
 if($consumer.ExitCode -ne $expectedExit){throw "Sync $phase failed; see ignored logs in $work"}
}
Push-Location $projectRoot
try{
 foreach($port in @(50051,18091)){if(Test-ProbePort $port){throw "Owned provider port $port occupied"}}
 if(-not $SkipBuild){Invoke-BMaven -JavaHome $jdk.Home -Arguments @('-B','package') *> "$work/build.log"}
 & (Join-Path $projectRoot 'scripts/provision-b-database.ps1') -TestDatabase -SkipBuild
 $TlsDirectory=Join-Path $work 'tls'
 & $java (Join-Path $AProject 'docs/tests/ab-v2-client/CreateTestCertificate.java') $TlsDirectory
 if($LASTEXITCODE -ne 0){throw 'Test TLS generation failed'}
 Import-ProbeEnvironment "$localA/app.env"
 Set-ProbeEnvironment 'B_SYNC_TEST_A_ACCESS_KEY' $env:AB_V2_ROCKETMQ_ACCESS_KEY
 Set-ProbeEnvironment 'B_SYNC_TEST_A_SECRET_KEY' $env:AB_V2_ROCKETMQ_SECRET_KEY
 $dbPassword=$env:PHASE1_DB_PASSWORD
 if(-not $dbPassword){$dbPassword=$env:SPRING_DATASOURCE_PASSWORD}
 if(-not $dbPassword){$dbPassword=& docker exec mysql sh -c 'printf "%s" "$MYSQL_ROOT_PASSWORD"';if($LASTEXITCODE -ne 0 -or -not $dbPassword){throw 'Supply external isolated A database credentials'}}
 # Capture A before importing B. A only accesses its existing isolated test schema.
 Set-ProbeEnvironment 'SPRING_DATASOURCE_PASSWORD' $dbPassword
 Set-ProbeEnvironment 'SPRING_DATASOURCE_URL' 'jdbc:mysql://127.0.0.1:13306/group_buy_market_phase1_test?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai'
 Set-ProbeEnvironment 'AB_V2_TLS_SERVER_CERT' "$TlsDirectory/certificate.pem"
 Set-ProbeEnvironment 'AB_V2_TLS_SERVER_KEY' "$TlsDirectory/private-key.pem"
 Set-ProbeEnvironment 'AB_V2_TLS_CLIENT_CA' "$TlsDirectory/certificate.pem"
 Set-ProbeEnvironment 'AB_V2_RPC_REQUIRE_TLS' true
 Set-ProbeEnvironment 'DUBBO_PROTOCOL_SSL_ENABLED' true
 Set-ProbeEnvironment 'DUBBO_SSL_SERVER_KEY_CERT_CHAIN_PATH' "$TlsDirectory/certificate.pem"
 Set-ProbeEnvironment 'DUBBO_SSL_SERVER_PRIVATE_KEY_PATH' "$TlsDirectory/private-key.pem"
 Set-ProbeEnvironment 'DUBBO_SSL_SERVER_TRUST_CERT_COLLECTION_PATH' "$TlsDirectory/certificate.pem"
 $aEnvironment=@{};Get-ChildItem Env: | Where-Object {$_.Name -notlike 'B_*'} | ForEach-Object {$aEnvironment[$_.Name]=$_.Value}
 Import-ProbeEnvironment "$localA/b.env"
 foreach($name in @('SPRING_DATASOURCE_URL','SPRING_DATASOURCE_USERNAME','SPRING_DATASOURCE_PASSWORD')){Set-ProbeEnvironment $name $null}
 $credentials=Import-Clixml (Join-Path $projectRoot '.local/b02-test-database.credentials.xml')
 Set-ProbeEnvironment B_DATABASE_URL $credentials.Url
 Set-ProbeEnvironment B_DATABASE_USERNAME $credentials.Runtime.UserName
 Set-ProbeEnvironment B_DATABASE_PASSWORD $credentials.Runtime.GetNetworkCredential().Password
 Set-ProbeEnvironment B_DATABASE_SCOPE 'b02-test'
 Set-ProbeEnvironment B_DATABASE_ENABLED true
 Set-ProbeEnvironment B_MIGRATION_USERNAME $null
 Set-ProbeEnvironment B_MIGRATION_PASSWORD $null
 Set-ProbeEnvironment B_IDENTITY_ORIGIN 'http://127.0.0.1:5173'
 Set-ProbeEnvironment B_IDENTITY_SECURE_COOKIES false
 Set-ProbeEnvironment B_IDENTITY_KEY_ID 'b02-test'
 Set-ProbeEnvironment B_IDENTITY_PRIVATE_KEY_FILE (Join-Path $projectRoot '.local/b02-test-keys/private.pem')
 Set-ProbeEnvironment B_IDENTITY_PUBLIC_KEY_FILE (Join-Path $projectRoot '.local/b02-test-keys/public.pem')
 Set-ProbeEnvironment B_RPC_GROUP 'gbm-dev'
 Set-ProbeEnvironment B_RPC_URL 'tri://127.0.0.1:50051?ssl-enabled=true'
 Set-ProbeEnvironment B_RPC_TRUST_CERT "$TlsDirectory/certificate.pem"
 Set-ProbeEnvironment AB_V2_TLS_CLIENT_CERT "$TlsDirectory/certificate.pem"
 Set-ProbeEnvironment AB_V2_TLS_CLIENT_KEY "$TlsDirectory/private-key.pem"
 Set-ProbeEnvironment B_MQ_NAMESERVER '127.0.0.1:9876'
 Set-ProbeEnvironment B_MQ_SOURCE $env:AB_V2_RPC_SOURCE
 Set-ProbeEnvironment B_MQ_CHANNEL $env:AB_V2_RPC_CHANNEL
 Set-ProbeEnvironment B_MQ_PRODUCT_TOPIC 'B_PRODUCT_EVENTS-dev'
 Set-ProbeEnvironment B_MQ_RESULT_TOPIC 'A_INTEGRATION_RESULTS-dev'
 Set-ProbeEnvironment B_MQ_TEAM_TOPIC 'A_TEAM_EVENTS-dev'
 Set-ProbeEnvironment B_MQ_RESULT_GROUP 'B_PRODUCT_SYNC_RESULTS-dev'
 Set-ProbeEnvironment B_MQ_USE_TLS false
 Set-ProbeEnvironment B_MQ_ALLOW_PLAINTEXT_LOOPBACK true
 Set-ProbeEnvironment B_SYNC_ACCELERATED_TEST true
 Set-ProbeEnvironment B_SYNC_QUERY_MILLIS 2000
 Set-ProbeEnvironment B_SYNC_WORK $work
 # Grant only the existing local B ACL account's dedicated sync/test subscriptions.
 $aclPath=Join-Path $localA 'plain_acl.yml';$acl=[IO.File]::ReadAllText($aclPath)
 $marker='  - accessKey: ABDevAppB';$start=$acl.IndexOf($marker)
 if($start -lt 0){throw 'Expected local B ACL account missing'}
 $before=$acl.Substring(0,$start);$bAcl=$acl.Substring($start)
 foreach($group in @('B_PRODUCT_SYNC_RESULTS-dev','B_SYNC_RETRY_TEST-dev','B_SYNC_DLQ_READER-dev')){if(-not $bAcl.Contains("- $group=")){$bAcl=$bAcl.TrimEnd()+"`n      - $group=PUB|SUB`n"}}
 if(-not $bAcl.Contains('%DLQ%B_SYNC_RETRY_TEST-dev=SUB')){$bAcl=$bAcl.Replace('    groupPerms:',"      - `"%DLQ%B_SYNC_RETRY_TEST-dev=SUB`"`n    groupPerms:")}
 if($acl -ne $before+$bAcl){[IO.File]::WriteAllText($aclPath,$before+$bAcl)}
 Start-Sleep -Seconds 4
 Invoke-SyncPhase prepare
 $current=@{};Get-ChildItem Env: | ForEach-Object {$current[$_.Name]=$_.Value}
 foreach($name in $current.Keys){if(-not $aEnvironment.ContainsKey($name)){[Environment]::SetEnvironmentVariable($name,$null,'Process')}}
 foreach($name in $aEnvironment.Keys){[Environment]::SetEnvironmentVariable($name,$aEnvironment[$name],'Process')}
 try{$provider=Start-Process -FilePath (Join-Path $AJavaHome 'bin/java.exe') -WindowStyle Hidden -PassThru -WorkingDirectory $localA -ArgumentList @('-jar',$aJar,'--server.port=18091','--spring.profiles.active=dev,v2-tls') -RedirectStandardOutput "$work/a.stdout.log" -RedirectStandardError "$work/a.stderr.log"}
 finally{Get-ChildItem Env: | ForEach-Object {if(-not $current.ContainsKey($_.Name)){[Environment]::SetEnvironmentVariable($_.Name,$null,'Process')}};foreach($name in $current.Keys){[Environment]::SetEnvironmentVariable($name,$current[$name],'Process')}}
 $readyBy=[DateTime]::UtcNow.AddSeconds(60)
 while(-not(Test-ProbePort 50051)){if($provider.HasExited -or [DateTime]::UtcNow -gt $readyBy){throw 'Owned isolated A did not become ready'};Start-Sleep -Milliseconds 300}
 Invoke-SyncPhase verify
 Get-Content "$work/verify.txt"
 if($AckRestart){Invoke-SyncPhase ack-commit 86;if(-not(Test-Path "$work/ack-committed.json")){throw 'Expected durable pre-ACK marker missing'};Invoke-SyncPhase ack-recover;Get-Content "$work/ack-recovery.txt"}
 if($Browser){
  & (Join-Path $PSScriptRoot 'run-b02-products-browser.ps1') -JavaHome $jdk.Home -SkipBuild
  & (Join-Path $PSScriptRoot 'run-b02-sync-browser.ps1') -JavaHome $jdk.Home -SkipBuild
 }
}finally{
 foreach($process in @($consumer,$provider)){if($process -and -not $process.HasExited){Stop-Process -Id $process.Id -Force}}
 foreach($name in $previousEnvironment.Keys){Restore-BEnvironmentVariable $name $previousEnvironment[$name]}
 Pop-Location
}
