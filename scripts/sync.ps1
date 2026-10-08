[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$QuarantineId,[string]$DatabaseCredentialFile='',[string]$JavaHome='', [switch]$TestDatabase,[switch]$SkipBuild)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot 'b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome
if($QuarantineId -notmatch '^[A-Za-z0-9._-]{1,64}$'){throw 'Invalid quarantine identifier'}
if(-not $DatabaseCredentialFile -and -not $env:B_DATABASE_URL){$DatabaseCredentialFile=Join-Path $root $(if($TestDatabase){'.local/b02-test-database.credentials.xml'}else{'.local/database.credentials.xml'})}
$names=@('B_DATABASE_ENABLED','B_DATABASE_URL','B_DATABASE_USERNAME','B_DATABASE_PASSWORD','B_DATABASE_SCOPE','B_MIGRATION_USERNAME','B_MIGRATION_PASSWORD','B_SYNC_TEST_A_ACCESS_KEY','B_SYNC_TEST_A_SECRET_KEY')
$previous=@{};foreach($name in $names){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
Push-Location $root
try{
 if($DatabaseCredentialFile){
  $c=Import-Clixml -LiteralPath $DatabaseCredentialFile
  $schema=if($TestDatabase){'zj_market_b02_test'}else{'zj_market'};$account=if($TestDatabase){'zj_market_b02_test_app'}else{'zj_market_app'}
  if($c.Runtime.UserName -ne $account -or $c.Url -notmatch "^jdbc:mysql://[^/]+/$schema(?:\?.*)?$"){throw 'Explicit B runtime account and schema required'}
  Restore-BEnvironmentVariable B_DATABASE_URL $c.Url
  Restore-BEnvironmentVariable B_DATABASE_USERNAME $c.Runtime.UserName
  Restore-BEnvironmentVariable B_DATABASE_PASSWORD $c.Runtime.GetNetworkCredential().Password
  Restore-BEnvironmentVariable B_DATABASE_SCOPE $(if($TestDatabase){'b02-test'}else{'development'})
 }
 Restore-BEnvironmentVariable B_DATABASE_ENABLED true
 foreach($name in @('B_MIGRATION_USERNAME','B_MIGRATION_PASSWORD','B_SYNC_TEST_A_ACCESS_KEY','B_SYNC_TEST_A_SECRET_KEY')){Restore-BEnvironmentVariable $name $null}
 if(-not $SkipBuild){Invoke-BMaven -JavaHome $jdk.Home -Arguments @('-B','-pl','zj-market-verification','-am','package')}
 & $jdk.Java '-jar' (Join-Path $root 'zj-market-verification/target/zj-market-verification.jar') '--sync' 'replay' $QuarantineId
 if($LASTEXITCODE -ne 0){throw 'Trusted quarantine replay failed; record retained for investigation'}
}finally{foreach($name in $names){Restore-BEnvironmentVariable $name $previous[$name]};Pop-Location}
