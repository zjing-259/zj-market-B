[CmdletBinding()]
param([string]$JavaHome='', [string]$AJavaHome='D:/Dev_tools/2.environment/jdk/jdk8', [string]$RunName='', [switch]$SkipBuild, [switch]$Browser, [switch]$ScopedBrowser)
$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $projectRoot 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome;$java=$jdk.Java
$AProject=Join-Path (Split-Path $projectRoot -Parent) 'group-buy-market'
$localA=Join-Path $AProject 'docs/dev-ops/ab-v2/.local'
$aJar=Join-Path $AProject 'group-buy-market-app/target/group-buy-market-app.jar'
$bJar=Join-Path $projectRoot 'zj-market-verification/target/zj-market-verification.jar'
if(-not $RunName){$RunName='b025-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($RunName -notmatch '^[a-zA-Z0-9-]+$'){throw 'Invalid run name'}
$work=Join-Path $projectRoot "target/trial/$RunName"
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

function Invoke-TrialPhase([string]$phase){
 $script:consumer=Start-Process -FilePath $java -WindowStyle Hidden -PassThru -WorkingDirectory $projectRoot -ArgumentList @('-jar',$bJar,'--trial',$phase) -RedirectStandardOutput "$work/$phase.stdout.log" -RedirectStandardError "$work/$phase.stderr.log"
 Wait-ProbeProcess $consumer 240
 if($consumer.ExitCode -ne 0){throw "Trial $phase failed; see ignored logs in $work"}
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
 Set-ProbeEnvironment B_TRIAL_WORK $work
 foreach($role in @('', 'MEMBER_', 'OP_')) {
  Set-ProbeEnvironment ("B_TRIAL_TEST_"+$role+'LOGIN_NAME') ('trial-'+$role.ToLower()+[guid]::NewGuid().ToString('N').Substring(0,12))
  Set-ProbeEnvironment ("B_TRIAL_TEST_"+$role+'PASSWORD') ([guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N'))
 }
 Invoke-TrialPhase prepare
 $fixture=Get-Content "$work/fixtures.json" -Raw | ConvertFrom-Json
 $oldMysqlPwd=$env:MYSQL_PWD
 try {
  $capacity="SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='group_buy_market_phase1_test' AND ((table_name='sc_sku_activity' AND column_name='goods_id') OR (table_name='crowd_tags_detail' AND column_name='user_id')) AND character_maximum_length>=64;" | & docker exec -i mysql sh -c 'MYSQL_PWD=$MYSQL_ROOT_PASSWORD exec mysql -uroot -N -B'
  if($LASTEXITCODE -ne 0 -or "$capacity".Trim() -ne '2'){throw 'A isolated fixture columns require the existing 64-character migration'}
  if($fixture.discountId -notmatch '^[a-z0-9]{8}$' -or $fixture.tagId -notmatch '^[a-zA-Z0-9-]{1,32}$' -or $fixture.memberId -notmatch '^[a-zA-Z0-9-]{1,64}$'){throw 'Invalid fixture identifiers'}
  $sql="INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) VALUES('$($fixture.discountId)','B025 isolated','B025 own fixture',0,'ZJ','10');"
  foreach($key in @('public','ineligible','hidden','race')) {
   $row=$fixture.$key
   if($row.goodsId -notmatch '^[a-zA-Z0-9-]{1,64}$' -or $row.activityId -notmatch '^[0-9]{12}$'){throw 'Invalid fixture identifiers'}
   $tag='NULL';$scope='NULL'
   if($key -eq 'ineligible' -or $key -eq 'hidden'){$tag="'$($fixture.tagId)'";$scope=if($key -eq 'hidden'){"'1,2'"}else{"'0,2'"}}
   $sql+="INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time,tag_id,tag_scope) VALUES($($row.activityId),'B025 isolated','$($fixture.discountId)',0,1,3,60,1,DATE_SUB(NOW(),INTERVAL 1 DAY),DATE_ADD(NOW(),INTERVAL 1 DAY),$tag,$scope);"
   $sql+="INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES('s01','c01',$($row.activityId),'$($row.goodsId)');"
  }
  $sql+="INSERT INTO crowd_tags(tag_id,tag_name,tag_desc,statistics) VALUES('$($fixture.tagId)','B025 own tag','B025 isolated fixture',1);"
  $sql+="INSERT INTO crowd_tags_detail(tag_id,user_id) VALUES('$($fixture.tagId)','$($fixture.memberId)');"
  $sql | & docker exec -i mysql sh -c 'MYSQL_PWD=$MYSQL_ROOT_PASSWORD exec mysql -uroot group_buy_market_phase1_test'
  if($LASTEXITCODE -ne 0){throw 'Own isolated A fixture insertion failed'}
 } finally {Restore-BEnvironmentVariable MYSQL_PWD $oldMysqlPwd}

 $current=@{};Get-ChildItem Env: | ForEach-Object {$current[$_.Name]=$_.Value}
 foreach($name in $current.Keys){if(-not $aEnvironment.ContainsKey($name)){[Environment]::SetEnvironmentVariable($name,$null,'Process')}}
 foreach($name in $aEnvironment.Keys){[Environment]::SetEnvironmentVariable($name,$aEnvironment[$name],'Process')}
 try{$provider=Start-Process -FilePath (Join-Path $AJavaHome 'bin/java.exe') -WindowStyle Hidden -PassThru -WorkingDirectory $localA -ArgumentList @('-jar',$aJar,'--server.port=18091','--spring.profiles.active=dev,v2-tls') -RedirectStandardOutput "$work/a.stdout.log" -RedirectStandardError "$work/a.stderr.log"}
 finally{Get-ChildItem Env: | ForEach-Object {if(-not $current.ContainsKey($_.Name)){[Environment]::SetEnvironmentVariable($_.Name,$null,'Process')}};foreach($name in $current.Keys){[Environment]::SetEnvironmentVariable($name,$current[$name],'Process')}}
 $readyBy=[DateTime]::UtcNow.AddSeconds(60)
 while(-not(Test-ProbePort 50051)){if($provider.HasExited -or [DateTime]::UtcNow -gt $readyBy){throw 'Owned isolated A did not become ready'};Start-Sleep -Milliseconds 300}
 Invoke-TrialPhase verify
 Get-Content "$work/verify.txt"
 if($Browser){ & (Join-Path $PSScriptRoot 'run-b02-trial-browser.ps1') -JavaHome $jdk.Home -SkipBuild -ScopedBackground:$ScopedBrowser; Copy-Item target/b025-browser-run.txt "$work/live-browser-run.txt";Copy-Item target/trial/browser.txt "$work/browser.txt" }
 Stop-Process -Id $provider.Id -Force
 $provider.WaitForExit()
 if($Browser){ & (Join-Path $PSScriptRoot 'run-b02-trial-browser.ps1') -JavaHome $jdk.Home -SkipBuild -Offline;Copy-Item target/b025-browser-run.txt "$work/offline-browser-run.txt";Copy-Item target/trial/browser-offline.txt "$work/browser-offline.txt" }
 Invoke-TrialPhase offline
 Get-Content "$work/offline.txt"
}finally{
 foreach($process in @($consumer,$provider)){if($process -and -not $process.HasExited){Stop-Process -Id $process.Id -Force}}
 foreach($name in $previousEnvironment.Keys){Restore-BEnvironmentVariable $name $previousEnvironment[$name]}
 Pop-Location
}
