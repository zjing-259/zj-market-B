[CmdletBinding()]
param([string]$JavaHome='', [string]$AJavaHome='D:/Dev_tools/2.environment/jdk/jdk8', [string]$RunName='', [switch]$SkipBuild,[switch]$WithFulfillment,[switch]$WithPaymentClosing,[switch]$WithPayments,[switch]$WithSettlement,[switch]$WithLocalOrders,[switch]$WithTradeRecovery,[switch]$WithUnpaidClose,[switch]$WithJointFaults, [ValidateSet('prepare','verify')][string]$Mode='prepare')
$ErrorActionPreference='Stop'
if($WithFulfillment -and ($WithPayments -or $WithSettlement -or $WithPaymentClosing -or $WithUnpaidClose -or $WithJointFaults)){throw 'Fulfillment requires its own fresh batch'}
if($WithFulfillment){$WithTradeRecovery=$true}
if($WithPaymentClosing -and ($WithPayments -or $WithSettlement -or $WithUnpaidClose -or $WithJointFaults)){throw "PaymentClosing requires its own fresh batch"}
if($WithPaymentClosing){$WithTradeRecovery=$true}
if($WithSettlement){$WithPayments=$true}
if($WithPayments -and ($WithUnpaidClose -or $WithJointFaults)){throw "Payments requires its own batch; exposed orders cannot use old unpaid close probes"}
if($WithPayments){$WithTradeRecovery=$true}
if($WithJointFaults){$WithUnpaidClose=$true}
if($WithUnpaidClose){$WithTradeRecovery=$true}
if($WithTradeRecovery){$WithLocalOrders=$true}
if($WithLocalOrders -and $Mode -ne 'prepare'){throw 'WithLocalOrders requires a fresh prepare run; recover accepted business orders through their original-intent APIs.'}
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $projectRoot 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome;$java=$jdk.Java
$AProject=Join-Path (Split-Path $projectRoot -Parent) 'group-buy-market'
$localA=Join-Path $AProject 'docs/dev-ops/ab-v2/.local'
$aJar=Join-Path $AProject 'group-buy-market-app/target/group-buy-market-app.jar'
$bJar=Join-Path $projectRoot 'zj-market-verification/target/zj-market-verification.jar'
if($Mode -eq 'verify' -and -not $RunName){throw 'Verify requires the prepared RunName'}
if(-not $RunName){$RunName='b030-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($RunName -notmatch '^[a-zA-Z0-9-]+$'){throw 'Invalid run name'}
$work=Join-Path $projectRoot "target/b03-readiness/$RunName"
$baseWork=$work
$accountFile=Join-Path $projectRoot ".local/b03-$RunName.credentials.xml"
if($Mode -eq 'prepare' -and (Test-Path $work)){throw 'Use a fresh run name'}
if($Mode -eq 'verify'){
 if(-not(Test-Path "$work/fixtures.json") -or -not(Test-Path $accountFile)){throw 'Recovery requires a prepared run and external account credentials'}
 $work=Join-Path $baseWork ('rechecks/'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
 New-Item -ItemType Directory -Path $work -Force | Out-Null
 Copy-Item "$baseWork/fixtures.json" "$work/fixtures.json"
}

New-Item -ItemType Directory -Path $work -Force | Out-Null
$previousEnvironment=@{};$provider=$null;$consumer=$null;$completed=$false
$originalDefaultJava=(& java -version 2>&1 | Out-String).Trim()
foreach($privatePath in @($accountFile,(Join-Path $projectRoot '.local/b02-test-keys/private.pem'))){
 & git -C $projectRoot check-ignore --quiet --no-index -- $privatePath
 if($LASTEXITCODE -ne 0){throw 'External credentials must be ignored by Git'}
}
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

function Invoke-ReadinessPhase([string]$phase){
 $script:consumer=Start-Process -FilePath $java -WindowStyle Hidden -PassThru -WorkingDirectory $projectRoot -ArgumentList @('-jar',$bJar,'--b03-readiness',$phase) -RedirectStandardOutput "$work/$phase.stdout.log" -RedirectStandardError "$work/$phase.stderr.log"
 Wait-ProbeProcess $consumer 240
 if($consumer.ExitCode -ne 0){throw "Readiness $phase failed; see ignored logs in $work"}
}
function Start-OwnedProvider([string]$label){
 $providerCaller=@{};Get-ChildItem Env: | ForEach-Object {$providerCaller[$_.Name]=$_.Value}
 foreach($name in $providerCaller.Keys){if(-not $aEnvironment.ContainsKey($name)){[Environment]::SetEnvironmentVariable($name,$null,'Process')}}
 foreach($name in $aEnvironment.Keys){[Environment]::SetEnvironmentVariable($name,$aEnvironment[$name],'Process')}
 try{$ownedProvider=Start-Process -FilePath (Join-Path $AJavaHome 'bin/java.exe') -WindowStyle Hidden -PassThru -WorkingDirectory $localA -ArgumentList @('-jar',$aJar,'--server.port=18091','--spring.profiles.active=dev,v2-tls') -RedirectStandardOutput "$work/$label.stdout.log" -RedirectStandardError "$work/$label.stderr.log"}
 finally{Get-ChildItem Env: | ForEach-Object {if(-not $providerCaller.ContainsKey($_.Name)){[Environment]::SetEnvironmentVariable($_.Name,$null,'Process')}};foreach($name in $providerCaller.Keys){[Environment]::SetEnvironmentVariable($name,$providerCaller[$name],'Process')}}
 return $ownedProvider
}
Push-Location $projectRoot
try{
 foreach($port in @(50051,18091)){if(Test-ProbePort $port){throw "Owned provider port $port occupied"}}
 if(-not $SkipBuild){Invoke-BMaven -JavaHome $jdk.Home -Arguments @('-B','-o','package') *> "$work/build.log"}
 foreach($credential in @('database.credentials.xml','b02-test-database.credentials.xml')){
  foreach($action in @('migrate','verify')){
   & (Join-Path $projectRoot 'scripts/database.ps1') -Mode $action -JavaHome $jdk.Home -CredentialFile (Join-Path $projectRoot ".local/$credential") -SkipBuild *> "$work/$credential-$action.log"
   Copy-Item "target/database/$action.txt" "$work/$credential-$action.txt"
  }
 }
 if($Mode -eq 'prepare'){
  & (Join-Path $PSScriptRoot 'run-b01-environment.ps1') -JavaHome $jdk.Home -AJavaHome $AJavaHome -RunName "$RunName-baseline" -SkipBuild *> "$work/baseline.log"
  Copy-Item "target/environment-probe/$RunName-baseline/report.json" "$work/baseline.json"
 }else{Copy-Item "$baseWork/baseline.json" "$work/baseline.json"}
 if((Get-Content "$work/baseline.json" -Raw | ConvertFrom-Json).status -ne 'PASSED'){throw 'A passing middleware baseline is required'}
 @("B-head=$(& git rev-parse HEAD)","A-head=$(& git -C $AProject rev-parse HEAD)","B-JDK=$($jdk.Home)","A-JDK=$AJavaHome","A-contract-sha256=$((Get-FileHash "$AProject/docs/ab-api-contract.md").Hash)","A-jar-sha256=$((Get-FileHash $aJar).Hash)","B-verification-jar-sha256=$((Get-FileHash $bJar).Hash)") | Set-Content "$work/provenance.txt"
 foreach($file in @('docs/tests/run-b03-readiness.ps1','zj-market-verification/src/main/java/cn/zj/zjmarket/verification/B03ReadinessCommands.java','zj-market-app/target/zj-market-app.jar')){
  "$file=$((Get-FileHash (Join-Path $projectRoot $file)).Hash)" | Add-Content "$work/provenance.txt"
 }

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
 if($env:AB_V2_RPC_SOURCE -ne 's01' -or $env:AB_V2_RPC_CHANNEL -ne 'c01'){throw 'This isolated fixture requires the existing s01/c01 scope'}
 Set-ProbeEnvironment B_MQ_PRODUCT_TOPIC 'B_PRODUCT_EVENTS-dev'
 Set-ProbeEnvironment B_MQ_RESULT_TOPIC 'A_INTEGRATION_RESULTS-dev'
 Set-ProbeEnvironment B_MQ_TEAM_TOPIC 'A_TEAM_EVENTS-dev'
 Set-ProbeEnvironment B_MQ_RESULT_GROUP 'B_PRODUCT_SYNC_RESULTS-dev'
 Set-ProbeEnvironment B_MQ_TRADE_TOPIC 'B_TRADE_EVENTS-dev'
 Set-ProbeEnvironment B_MQ_TRADE_RESULT_GROUP 'B_INTEGRATION_RESULTS-dev'
 Set-ProbeEnvironment B_MQ_TRADE_TEAM_GROUP 'B_TEAM_EVENTS-dev'
 Set-ProbeEnvironment B_MQ_USE_TLS false
 Set-ProbeEnvironment B_MQ_ALLOW_PLAINTEXT_LOOPBACK true
 Set-ProbeEnvironment B_SYNC_ACCELERATED_TEST true
 Set-ProbeEnvironment B_SYNC_QUERY_MILLIS 2000
 Set-ProbeEnvironment B03_WORK $work
 Set-ProbeEnvironment B03_WITH_UNPAID_CLOSE $(if($WithUnpaidClose){'true'}else{'false'})
 Set-ProbeEnvironment B03_WITH_TRADE_RECOVERY $(if($WithTradeRecovery){'true'}else{'false'})
 Set-ProbeEnvironment B03_WITH_LOCAL_ORDERS $(if($WithLocalOrders){'true'}else{'false'})
 if($Mode -eq 'prepare'){
  $accounts=@{}
  foreach($role in @('USER','MEMBER','SECOND','THIRD','OP')){
   $login='b030-'+$role.ToLower()+'-'+[guid]::NewGuid().ToString('N').Substring(0,10)
   $password=[guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N')
   $accounts[$role]=[pscredential]::new($login,(ConvertTo-SecureString $password -AsPlainText -Force))
  }
  $accounts | Export-Clixml -LiteralPath $accountFile
 }else{$accounts=Import-Clixml -LiteralPath $accountFile}
 foreach($role in $accounts.Keys){
  Set-ProbeEnvironment ("B03_TEST_"+$role+"_LOGIN_NAME") $accounts[$role].UserName
  Set-ProbeEnvironment ("B03_TEST_"+$role+"_PASSWORD") $accounts[$role].GetNetworkCredential().Password
 }
 if($Mode -eq 'prepare'){
  Invoke-ReadinessPhase prepare
  $fixture=Get-Content "$work/fixtures.json" -Raw | ConvertFrom-Json
  $capacity="SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='group_buy_market_phase1_test' AND ((table_name='sc_sku_activity' AND column_name='goods_id') OR (table_name='crowd_tags_detail' AND column_name='user_id')) AND character_maximum_length>=64;" | & docker exec -i mysql sh -c 'MYSQL_PWD=$MYSQL_ROOT_PASSWORD exec mysql -uroot -N -B'
  if($LASTEXITCODE -ne 0 -or "$capacity".Trim() -ne '2'){throw 'Existing A test migration is required'}
  if($fixture.discountId -notmatch '^[0-9]{8}$' -or $fixture.tagId -notmatch '^[a-zA-Z0-9-]{1,32}$' -or $fixture.users.MEMBER -notmatch '^[a-zA-Z0-9-]{1,64}$'){throw 'Invalid fixture identifiers'}
  $sql="START TRANSACTION;INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr) VALUES('$($fixture.discountId)','B030 isolated','B030 own fixture',0,'ZJ','10');"
  foreach($key in @('open','full','expired','ineligible')){
   $row=$fixture.$key
   if($row.goodsId -notmatch '^[a-zA-Z0-9-]{1,64}$' -or $row.activityId -notmatch '^[0-9]{12}$'){throw 'Invalid fixture identifiers'}
   $tag='NULL';$scope='NULL';$target=if($key -eq 'full'){2}else{3}
   if($key -eq 'ineligible'){$tag="'$($fixture.tagId)'";$scope="'0,2'"}
   $end=if($key -eq 'expired'){'DATE_SUB(NOW(),INTERVAL 1 HOUR)'}else{'DATE_ADD(NOW(),INTERVAL 1 DAY)'}
   $sql+="INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time,tag_id,tag_scope) VALUES($($row.activityId),'B030 isolated','$($fixture.discountId)',0,10,$target,60,1,DATE_SUB(NOW(),INTERVAL 1 DAY),$end,$tag,$scope);"
   $sql+="INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES('s01','c01',$($row.activityId),'$($row.goodsId)');"
  }
  $sql+="INSERT INTO crowd_tags(tag_id,tag_name,tag_desc,statistics) VALUES('$($fixture.tagId)','B030 own tag','B030 isolated fixture',1);"
  $sql+="INSERT INTO crowd_tags_detail(tag_id,user_id) VALUES('$($fixture.tagId)','$($fixture.users.MEMBER)');"
  $sql+="COMMIT;"
  $sql | & docker exec -i mysql sh -c 'MYSQL_PWD=$MYSQL_ROOT_PASSWORD exec mysql -uroot group_buy_market_phase1_test'
  if($LASTEXITCODE -ne 0){throw 'Own isolated A fixture insertion failed'}
 }

 $provider=Start-OwnedProvider a
 $readyBy=[DateTime]::UtcNow.AddSeconds(60)
 while(-not(Test-ProbePort 50051)){if($provider.HasExited -or [DateTime]::UtcNow -gt $readyBy){throw 'Owned isolated A did not become ready'};Start-Sleep -Milliseconds 300}
 Invoke-ReadinessPhase verify
 if($WithTradeRecovery){Invoke-ReadinessPhase trade-recover;if(-not((Get-Content "$work/trade-recover.txt") -contains 'status=PASSED')){throw 'Trade process restart report incomplete'}}
 if($WithSettlement){Set-ProbeEnvironment B03_WITH_SETTLEMENT true}
 if($WithFulfillment){Invoke-ReadinessPhase fulfillment;if(-not((Get-Content "$work/fulfillment.txt") -contains "status=PASSED")){throw "Actual A fulfillment incomplete"}}
 if($WithPaymentClosing){Invoke-ReadinessPhase payment-closing;if(-not((Get-Content "$work/payment-closing.txt") -contains "status=PASSED")){throw "Actual A exposed close incomplete"}}
 if($WithPayments){Invoke-ReadinessPhase payments;if(-not((Get-Content "$work/payments.txt") -contains "status=PASSED")){throw "Actual A payment probe incomplete"}}
 if($WithSettlement){Invoke-ReadinessPhase settlement;if(-not((Get-Content "$work/settlement.txt") -contains "status=PASSED")){throw "Actual A settlement probe incomplete"}}
 if($WithUnpaidClose){Invoke-ReadinessPhase close-recover;if(-not((Get-Content "$work/close-recover.txt") -contains 'status=PASSED')){throw 'Unpaid close restart report incomplete'}}
 if($WithJointFaults){
  Invoke-ReadinessPhase close-outage-prepare
  $firstProviderPid=$provider.Id
  Stop-Process -Id $provider.Id -Force;$null=$provider.WaitForExit(5000)
  $offlineBy=[DateTime]::UtcNow.AddSeconds(10)
  while((Test-ProbePort 50051) -or (Test-ProbePort 18091)){if([DateTime]::UtcNow -ge $offlineBy){throw 'Owned A provider did not stop'};Start-Sleep -Milliseconds 200}
  Invoke-ReadinessPhase close-outage
  if(-not((Get-Content "$work/close-outage.txt") -contains 'status=PASSED')){throw 'Actual A outage did not preserve held stock'}
  $provider=Start-OwnedProvider a-restarted
  if($provider.Id -eq $firstProviderPid){throw 'Expected actual new A process'}
  $readyBy=[DateTime]::UtcNow.AddSeconds(60)
  while(-not(Test-ProbePort 50051)){if($provider.HasExited -or [DateTime]::UtcNow -gt $readyBy){throw 'Owned A restart failed'};Start-Sleep -Milliseconds 300}
  Invoke-ReadinessPhase close-outage-recover
  if((Get-Content "$work/close-outage-recovery.json" -Raw | ConvertFrom-Json).status -ne 'PASSED'){throw 'Actual outage recovery incomplete'}
  @{status='PASSED';oldProviderPid=$firstProviderPid;newProviderPid=$provider.Id;sharedMiddlewareStopped=$false} | ConvertTo-Json | Set-Content "$work/a-outage-processes.json"
 }
 if(-not((Get-Content "$work/verify.txt") -contains 'status=PASSED')){throw 'Readiness report is incomplete'}
 $completed=$true
 Get-Content "$work/verify.txt"

}finally{
 foreach($process in @($consumer,$provider)){
  if($process -and -not $process.HasExited){Stop-Process -Id $process.Id -Force;$null=$process.WaitForExit(5000)}
 }
 $releaseBy=[DateTime]::UtcNow.AddSeconds(10)
 while((Test-ProbePort 50051) -or (Test-ProbePort 18091)){
  if([DateTime]::UtcNow -ge $releaseBy){break}
  Start-Sleep -Milliseconds 200
 }
 $released=(-not(Test-ProbePort 50051) -and -not(Test-ProbePort 18091))
 foreach($name in $previousEnvironment.Keys){Restore-BEnvironmentVariable $name $previousEnvironment[$name]}
 $restored=$true
 foreach($name in $previousEnvironment.Keys){
  if([Environment]::GetEnvironmentVariable($name,'Process') -cne $previousEnvironment[$name]){$restored=$false}
 }
 $defaultJava=(& java -version 2>&1 | Out-String).Trim()
 $javaUnchanged=$defaultJava -ceq $originalDefaultJava
 @("environment-restored=$restored","owned-ports-released=$released","default-java-unchanged=$javaUnchanged",$defaultJava) | Set-Content "$work/cleanup.txt"
 $passed=$completed -and $restored -and $released -and $javaUnchanged
 @{status=$(if($passed){'PASSED'}else{'FAILED'});runName=$RunName;mode=$Mode;environmentRestored=$restored;ownedPortsReleased=$released;defaultJavaUnchanged=$javaUnchanged;fixtureSha256=(Get-FileHash "$work/fixtures.json" -ErrorAction SilentlyContinue).Hash;inventory=$(if($WithLocalOrders){'OPERATOR_APPLIED'}else{'PLAN_ONLY'});verifiedAt=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content "$work/report.json"
 Pop-Location
 if($completed -and -not $passed){throw 'Readiness cleanup verification failed'}
}
