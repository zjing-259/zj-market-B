[CmdletBinding()]
param(
    [ValidateSet('migrate','verify')][string]$Mode = 'verify',
    [string]$JavaHome = '',
    [string]$CredentialFile = '',
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot 'b-runtime.ps1')
$jdk = Resolve-BJava $JavaHome
if (-not $CredentialFile -and -not $env:B_DATABASE_URL) {
    $CredentialFile = Join-Path $root '.local/database.credentials.xml'
}
if ($CredentialFile -and -not (Test-Path -LiteralPath $CredentialFile)) {
    throw 'Explicit credential file does not exist.'
}
$names = @('B_DATABASE_ENABLED','B_DATABASE_URL','B_DATABASE_USERNAME','B_DATABASE_PASSWORD',
    'B_MIGRATION_USERNAME','B_MIGRATION_PASSWORD','B_DATABASE_REPORT','B_DATABASE_SCOPE')
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
Push-Location $root
try {
    if ($CredentialFile) {
        # Export-Clixml PSCredential uses Windows DPAPI, tied to this machine/user.
        $credentials = Import-Clixml -LiteralPath $CredentialFile
        $values = @{
            B_DATABASE_SCOPE = $(if ($credentials.Scope) { $credentials.Scope } else { 'development' })
            B_DATABASE_URL = $credentials.Url
            B_DATABASE_USERNAME = $credentials.Runtime.UserName
            B_DATABASE_PASSWORD = $credentials.Runtime.GetNetworkCredential().Password
            B_MIGRATION_USERNAME = $credentials.Migration.UserName
            B_MIGRATION_PASSWORD = $credentials.Migration.GetNetworkCredential().Password
        }
        foreach ($name in $values.Keys) { Restore-BEnvironmentVariable $name $values[$name] }
    }
    if ($Mode -eq 'verify') {
        Restore-BEnvironmentVariable 'B_MIGRATION_USERNAME' $null
        Restore-BEnvironmentVariable 'B_MIGRATION_PASSWORD' $null
    } else {
        Restore-BEnvironmentVariable 'B_DATABASE_USERNAME' $null
        Restore-BEnvironmentVariable 'B_DATABASE_PASSWORD' $null
    }
    if (-not $env:B_DATABASE_URL) { throw 'Supply external B_DATABASE_URL and database credentials.' }
    $report = Join-Path $root ("target/database/" + $Mode + '.txt')
    New-Item -ItemType Directory -Path (Split-Path $report -Parent) -Force | Out-Null
    [IO.File]::WriteAllText($report, "status=RUNNING")
    Restore-BEnvironmentVariable 'B_DATABASE_REPORT' $report
    Restore-BEnvironmentVariable 'B_DATABASE_ENABLED' 'true'
    if (-not $SkipBuild) {
        Invoke-BMaven -JavaHome $jdk.Home -Arguments @('-B','-pl','zj-market-verification','-am','package')
    }
    $jar = Join-Path $root 'zj-market-verification/target/zj-market-verification.jar'
    if (-not (Test-Path -LiteralPath $jar)) { throw 'Build B verification before -SkipBuild.' }
    & $jdk.Java '-jar' $jar '--database' $Mode
    if ($LASTEXITCODE -ne 0) { throw "B database $Mode failed; inspect permission/configuration checks." }
    Write-Host ("Report: " + $report)
} finally {
    foreach ($name in $names) { Restore-BEnvironmentVariable $name $previous[$name] }
    Pop-Location
}
