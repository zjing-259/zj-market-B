[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$JavaHome = '',
    [switch]$SkipBuild,
    [string]$DatabaseCredentialFile = '',
    [ValidateSet('development','b02-test')][string]$DatabaseScope='development',
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)][string[]]$ApplicationArguments = @()
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'b-runtime.ps1')
$jdk = Resolve-BJava $JavaHome
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$previousJavaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Process')
$previousPath = [Environment]::GetEnvironmentVariable('PATH', 'Process')
$databaseNames = @('B_DATABASE_ENABLED','B_DATABASE_URL','B_DATABASE_USERNAME','B_DATABASE_PASSWORD',
    'B_MIGRATION_USERNAME','B_MIGRATION_PASSWORD','B_DATABASE_SCOPE','B_OPERATOR_LOGIN_NAME','B_OPERATOR_PASSWORD','B_OPERATOR_DISPLAY_NAME','B_BROWSER_OPERATOR_LOGIN_NAME','B_BROWSER_OPERATOR_PASSWORD','B_SYNC_TEST_A_ACCESS_KEY','B_SYNC_TEST_A_SECRET_KEY','B_TRIAL_TEST_LOGIN_NAME','B_TRIAL_TEST_PASSWORD','B_TRIAL_TEST_MEMBER_LOGIN_NAME','B_TRIAL_TEST_MEMBER_PASSWORD','B_TRIAL_TEST_OP_LOGIN_NAME','B_TRIAL_TEST_OP_PASSWORD')
$databasePrevious = @{}
foreach ($name in $databaseNames) { $databasePrevious[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
Push-Location $projectRoot
try {
    if ($DatabaseCredentialFile) {
        $credentials = Import-Clixml -LiteralPath $DatabaseCredentialFile
        $expectedUser = if ($DatabaseScope -eq 'b02-test') { 'zj_market_b02_test_app' } else { 'zj_market_app' }
        $expectedSchema = if ($DatabaseScope -eq 'b02-test') { 'zj_market_b02_test' } else { 'zj_market' }
        if ($credentials.Runtime.UserName -ne $expectedUser -or $credentials.Url -notmatch "^jdbc:mysql://[^/]+/$expectedSchema(?:\?.*)?$") { throw 'Expected explicit B runtime database scope/account.' }
        Restore-BEnvironmentVariable 'B_DATABASE_SCOPE' $DatabaseScope
        Restore-BEnvironmentVariable 'B_DATABASE_ENABLED' 'true'
        Restore-BEnvironmentVariable 'B_DATABASE_URL' $credentials.Url
        Restore-BEnvironmentVariable 'B_DATABASE_USERNAME' $credentials.Runtime.UserName
        Restore-BEnvironmentVariable 'B_DATABASE_PASSWORD' $credentials.Runtime.GetNetworkCredential().Password
    }
    # Ordinary B receives only runtime credentials, including external-env launches.
    Restore-BEnvironmentVariable 'B_MIGRATION_USERNAME' $null
    Restore-BEnvironmentVariable 'B_MIGRATION_PASSWORD' $null
    foreach ($name in @('B_OPERATOR_LOGIN_NAME','B_OPERATOR_PASSWORD','B_OPERATOR_DISPLAY_NAME','B_BROWSER_OPERATOR_LOGIN_NAME','B_BROWSER_OPERATOR_PASSWORD','B_SYNC_TEST_A_ACCESS_KEY','B_SYNC_TEST_A_SECRET_KEY','B_TRIAL_TEST_LOGIN_NAME','B_TRIAL_TEST_PASSWORD','B_TRIAL_TEST_MEMBER_LOGIN_NAME','B_TRIAL_TEST_MEMBER_PASSWORD','B_TRIAL_TEST_OP_LOGIN_NAME','B_TRIAL_TEST_OP_PASSWORD')) { Restore-BEnvironmentVariable $name $null }
    if (-not $SkipBuild) { Invoke-BMaven -JavaHome $jdk.Home -Arguments @('-B','-pl','zj-market-app','-am','package') }
    $jar = Join-Path $projectRoot 'zj-market-app/target/zj-market-app-exec.jar'
    if (-not (Test-Path -LiteralPath $jar)) { throw 'Build B first or omit -SkipBuild.' }
    [Environment]::SetEnvironmentVariable('JAVA_HOME', $jdk.Home, 'Process')
    [Environment]::SetEnvironmentVariable('PATH', (Join-Path $jdk.Home 'bin') + [IO.Path]::PathSeparator + $previousPath, 'Process')
    & $jdk.Java '-jar' $jar @ApplicationArguments
    if ($LASTEXITCODE -ne 0) { throw "B exited with code $LASTEXITCODE." }
} finally {
    Restore-BEnvironmentVariable -Name 'JAVA_HOME' -Value $previousJavaHome
    Restore-BEnvironmentVariable -Name 'PATH' -Value $previousPath
    foreach ($name in $databaseNames) { Restore-BEnvironmentVariable $name $databasePrevious[$name] }
    Pop-Location
}
