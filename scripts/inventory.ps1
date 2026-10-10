[CmdletBinding()]
param([string]$CredentialFile='',[string]$JavaHome='', [switch]$SkipBuild)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot 'b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome
if (-not $CredentialFile -and -not $env:B_DATABASE_URL) {
    $CredentialFile=Join-Path $root '.local/b02-test-database.credentials.xml'
}
$names=@('B_DATABASE_ENABLED','B_DATABASE_URL','B_DATABASE_USERNAME','B_DATABASE_PASSWORD','B_MIGRATION_USERNAME','B_MIGRATION_PASSWORD','B_DATABASE_SCOPE','B_INVENTORY_REPORT')
$previous=@{};foreach($name in $names){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
Push-Location $root
try {
    if($CredentialFile){
        $c=Import-Clixml -LiteralPath $CredentialFile
        Restore-BEnvironmentVariable B_DATABASE_URL $c.Url
        Restore-BEnvironmentVariable B_DATABASE_USERNAME $c.Runtime.UserName
        Restore-BEnvironmentVariable B_DATABASE_PASSWORD $c.Runtime.GetNetworkCredential().Password
        Restore-BEnvironmentVariable B_DATABASE_SCOPE $(if($c.Scope){$c.Scope}else{'development'})
    }
    if(($env:B_DATABASE_SCOPE -ne 'b02-test' -or $env:B_DATABASE_USERNAME -ne 'zj_market_b02_test_app' -or $env:B_DATABASE_URL -notmatch '^jdbc:mysql://[^/]+/zj_market_b02_test(?:\?.*)?$')){throw 'Inventory verification refuses development/A/missing test configuration.'}
    Restore-BEnvironmentVariable B_DATABASE_ENABLED true
    Restore-BEnvironmentVariable B_MIGRATION_USERNAME $null
    Restore-BEnvironmentVariable B_MIGRATION_PASSWORD $null
    $report=Join-Path $root 'target/inventory/verify.txt'
    New-Item -ItemType Directory -Path (Split-Path $report -Parent) -Force | Out-Null
    [IO.File]::WriteAllText($report,'status=RUNNING')
    Restore-BEnvironmentVariable B_INVENTORY_REPORT $report
    if(-not $SkipBuild){Invoke-BMaven -JavaHome $jdk.Home -Arguments @('-B','-pl','zj-market-verification','-am','package')}
    & $jdk.Java '-jar' (Join-Path $root 'zj-market-verification/target/zj-market-verification.jar') '--inventory'
    if($LASTEXITCODE -ne 0){[IO.File]::WriteAllText($report,'status=FAILED');throw "B inventory verification failed."}
}finally{foreach($name in $names){Restore-BEnvironmentVariable $name $previous[$name]};Pop-Location}
