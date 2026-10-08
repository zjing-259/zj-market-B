[CmdletBinding()]
param([string]$JavaHome = '', [switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
$credentialFile = Join-Path $root '.local/database.credentials.xml'
& (Join-Path $root 'scripts/provision-b-database.ps1') -JavaHome $JavaHome -SkipBuild:$SkipBuild
$credentials = Import-Clixml -LiteralPath $credentialFile
$names = @('B_DATABASE_ENABLED','B_DATABASE_URL','B_DATABASE_USERNAME','B_DATABASE_PASSWORD',
    'B_MIGRATION_USERNAME','B_MIGRATION_PASSWORD')
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
try {
    Restore-BEnvironmentVariable 'B_DATABASE_USERNAME' $credentials.Runtime.UserName
    Restore-BEnvironmentVariable 'B_MIGRATION_USERNAME' $null
    Restore-BEnvironmentVariable 'B_MIGRATION_PASSWORD' $null
    $cases = @(
        @{ Name='authentication-denied'; Url=$credentials.Url; Password='intentionally-invalid'; Match='sqlError=1045' },
        @{ Name='a-schema-denied'; Url='jdbc:mysql://127.0.0.1:13306/group_buy_market'; Password=$credentials.Runtime.GetNetworkCredential().Password; Match='error=IllegalStateException' }
    )
    foreach ($case in $cases) {
        Restore-BEnvironmentVariable 'B_DATABASE_URL' $case.Url
        Restore-BEnvironmentVariable 'B_DATABASE_PASSWORD' $case.Password
        $log = Join-Path $root ('target/database/' + $case.Name + '.log')
        $failed = $false
        try { & (Join-Path $root 'scripts/database.ps1') -Mode verify -JavaHome $JavaHome -SkipBuild *> $log }
        catch { $failed = $true }
        $report = Join-Path $root 'target/database/verify.txt'
        if (-not $failed -or (Get-Content -LiteralPath $report -Raw) -notmatch $case.Match) {
            throw ('Negative database case did not fail as expected: ' + $case.Name)
        }
        Copy-Item -LiteralPath $report -Destination (Join-Path $root ('target/database/' + $case.Name + '.txt'))
        Write-Host ($case.Name + ': correctly rejected')
    }
} finally {
    foreach ($name in $names) { Restore-BEnvironmentVariable $name $previous[$name] }
}
# Leave the main report at the final positive result.
& (Join-Path $root 'scripts/database.ps1') -Mode verify -CredentialFile $credentialFile -JavaHome $JavaHome -SkipBuild
$startupLog = Join-Path $root 'target/database/normal-start.log'
& (Join-Path $root 'scripts/start-b.ps1') -DatabaseCredentialFile $credentialFile -JavaHome $JavaHome -SkipBuild -ApplicationArguments @('--spring.main.web-application-type=none') *> $startupLog
foreach ($name in $names) {
    if ([Environment]::GetEnvironmentVariable($name,'Process') -cne $previous[$name]) {
        throw ('B script did not restore environment variable ' + $name)
    }
}
Write-Host 'B database acceptance: PASSED (migration, privileges, invalid password, wrong schema, normal startup and environment restoration).'
