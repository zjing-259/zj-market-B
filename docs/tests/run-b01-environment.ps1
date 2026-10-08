param(
    [string]$JavaHome = '',
    [string]$AJavaHome = 'D:/Dev_tools/2.environment/jdk/jdk8',
    [string]$AProject = '',
    [string]$RunName = 'verified',
    [string]$NettyVersion = '',
    [string]$TlsDirectory = '',
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $projectRoot 'scripts/b-runtime.ps1')
if (-not $AProject) { $AProject = Join-Path (Split-Path $projectRoot -Parent) 'group-buy-market' }
$AProject = (Resolve-Path $AProject).Path
if ($RunName -notmatch '^[a-zA-Z0-9-]+$') { throw 'RunName must be a simple label.' }
$work = Join-Path $projectRoot "target/environment-probe/$RunName"
New-Item -ItemType Directory -Path $work -Force | Out-Null
$localA = Join-Path $AProject 'docs/dev-ops/ab-v2/.local'
$aJar = Join-Path $AProject 'group-buy-market-app/target/group-buy-market-app.jar'
$bJar = Join-Path $projectRoot 'zj-market-verification/target/zj-market-verification.jar'
$previousEnvironment = @{}
$provider = $null
$consumer = $null
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
Push-Location $projectRoot
try {
    $jdk = Resolve-BJava $JavaHome
    $JavaHome = $jdk.Home
    $java = $jdk.Java
    foreach ($path in @($aJar, "$localA/app.env", "$localA/b.env")) {
        if (-not (Test-Path -LiteralPath $path)) { throw 'Existing A jar and ignored dev credentials are required.' }
    }
    foreach ($port in @(50051,18091)) {
        if (Test-ProbePort $port) { throw "Provider port $port is occupied; this script only manages its own isolated provider." }
    }
    foreach ($port in @(13306,16379,9876,10911)) {
        if (-not (Test-ProbePort $port)) { throw "Required local development service unavailable: $port" }
    }
    $versionArguments = @()
    if ($NettyVersion) { $versionArguments += "-Dnetty.version=$NettyVersion" }
    if (-not $SkipBuild) {
        Invoke-BMaven -JavaHome $JavaHome -Arguments (@('-B','-Dstyle.color=never') + $versionArguments + @('-pl','zj-market-verification','-am','package')) *> "$work/build.log"
        if ($LASTEXITCODE -ne 0) { throw 'Actual B build failed; see ignored build.log.' }
    }
    Invoke-BMaven -JavaHome $JavaHome -Arguments (@('-B','-Dstyle.color=never','dependency:tree','-Dverbose',"-DoutputFile=target/environment-probe/dependencies.txt") + $versionArguments) *> "$work/dependency-command.log"
    if ($LASTEXITCODE -ne 0) { throw 'Dependency audit failed.' }
    if (-not $TlsDirectory) {
        $TlsDirectory = "$work/tls"
        & $java (Join-Path $AProject 'docs/tests/ab-v2-client/CreateTestCertificate.java') $TlsDirectory
        if ($LASTEXITCODE -ne 0) { throw 'Local test certificate generation failed.' }
    }
    $TlsDirectory = (Resolve-Path $TlsDirectory).Path
    foreach ($file in @('certificate.pem','private-key.pem')) {
        if (-not (Test-Path (Join-Path $TlsDirectory $file))) { throw 'Local test certificate material missing.' }
    }

    Import-ProbeEnvironment "$localA/app.env"
    $dbPassword=$env:PHASE1_DB_PASSWORD
    if(-not $dbPassword){$dbPassword=$env:SPRING_DATASOURCE_PASSWORD}
    if(-not $dbPassword){$dbPassword=& docker exec mysql sh -c 'printf "%s" "$MYSQL_ROOT_PASSWORD"';if($LASTEXITCODE -ne 0 -or -not $dbPassword){throw 'Supply external isolated A database credentials'}}
    Set-ProbeEnvironment 'SPRING_DATASOURCE_PASSWORD' $dbPassword
    # Never run migrations or connect the provider to A's development business database.
    Set-ProbeEnvironment 'SPRING_DATASOURCE_URL' 'jdbc:mysql://127.0.0.1:13306/group_buy_market_phase1_test?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai'
    Set-ProbeEnvironment 'AB_V2_TLS_SERVER_CERT' "$TlsDirectory/certificate.pem"
    Set-ProbeEnvironment 'AB_V2_TLS_SERVER_KEY' "$TlsDirectory/private-key.pem"
    Set-ProbeEnvironment 'AB_V2_TLS_CLIENT_CA' "$TlsDirectory/certificate.pem"
    Set-ProbeEnvironment 'AB_V2_RPC_REQUIRE_TLS' 'true'
    Set-ProbeEnvironment 'DUBBO_PROTOCOL_SSL_ENABLED' 'true'
    Set-ProbeEnvironment 'DUBBO_SSL_SERVER_KEY_CERT_CHAIN_PATH' "$TlsDirectory/certificate.pem"
    Set-ProbeEnvironment 'DUBBO_SSL_SERVER_PRIVATE_KEY_PATH' "$TlsDirectory/private-key.pem"
    Set-ProbeEnvironment 'DUBBO_SSL_SERVER_TRUST_CERT_COLLECTION_PATH' "$TlsDirectory/certificate.pem"
    Set-ProbeEnvironment 'JAVA_HOME' $AJavaHome
    Set-ProbeEnvironment 'PATH' ((Join-Path $AJavaHome 'bin') + [IO.Path]::PathSeparator + $env:PATH)
    $provider = Start-Process -FilePath (Join-Path $AJavaHome 'bin/java.exe') -WindowStyle Hidden -PassThru -WorkingDirectory $localA `
        -ArgumentList @('-jar', $aJar, '--server.port=18091', '--spring.profiles.active=dev,v2-tls') `
        -RedirectStandardOutput "$work/a.stdout.log" -RedirectStandardError "$work/a.stderr.log"
    $readyBy = [DateTime]::UtcNow.AddSeconds(60)
    while (-not (Test-ProbePort 50051)) {
        if ($provider.HasExited) { throw 'Isolated A provider exited; inspect ignored A logs.' }
        if ([DateTime]::UtcNow -ge $readyBy) { throw 'Isolated A provider did not become ready.' }
        Start-Sleep -Milliseconds 500
    }

    # A already owns its environment snapshot; do not pass its datasource credentials to B.
    foreach ($name in @('SPRING_DATASOURCE_URL','SPRING_DATASOURCE_USERNAME','SPRING_DATASOURCE_PASSWORD')) {
        Set-ProbeEnvironment $name $null
    }
    Import-ProbeEnvironment "$localA/b.env"
    Set-ProbeEnvironment 'AB_V2_TLS_CLIENT_CERT' "$TlsDirectory/certificate.pem"
    Set-ProbeEnvironment 'AB_V2_TLS_CLIENT_KEY' "$TlsDirectory/private-key.pem"
    Set-ProbeEnvironment 'B_PROBE_RPC_URL' 'tri://127.0.0.1:50051?ssl-enabled=true'
    Set-ProbeEnvironment 'B_PROBE_REPORT' "$work/report.json"
    if (Test-Path -LiteralPath "$work/report.json") { Remove-Item -LiteralPath "$work/report.json" }
    Set-ProbeEnvironment 'JAVA_HOME' $JavaHome
    Set-ProbeEnvironment 'PATH' ((Join-Path $JavaHome 'bin') + [IO.Path]::PathSeparator + $previousEnvironment['PATH'])
    $consumer = Start-Process -FilePath $java -WindowStyle Hidden -PassThru -WorkingDirectory $projectRoot `
        -ArgumentList @('-jar', $bJar, '--spring.profiles.active=environment-probe') `
        -RedirectStandardOutput "$work/b.stdout.log" -RedirectStandardError "$work/b.stderr.log"
    Wait-ProbeProcess $consumer 120
    if (-not (Test-Path "$work/report.json")) { throw 'Actual B exited without a probe report; inspect ignored B logs.' }
    $report = Get-Content "$work/report.json" -Raw | ConvertFrom-Json
    $report | ConvertTo-Json -Depth 8
    if ($consumer.ExitCode -ne 0 -or $report.status -ne 'PASSED') { throw 'Actual B interoperability failed; inspect ignored report and logs.' }
} finally {
    foreach ($process in @($consumer,$provider)) {
        if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    }
    foreach ($name in $previousEnvironment.Keys) {
        Restore-BEnvironmentVariable -Name $name -Value $previousEnvironment[$name]
    }
    Pop-Location
}
