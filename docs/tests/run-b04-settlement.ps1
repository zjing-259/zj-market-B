[CmdletBinding()]
param([string]$JavaHome='', [string]$RunName='', [switch]$SkipBuild)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $root 'scripts/b-runtime.ps1')
$jdk=Resolve-BJava $JavaHome
if(-not $RunName){$RunName='b043-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($RunName -notmatch '^[a-zA-Z0-9-]+$'){throw 'Invalid run name'}
$work=Join-Path $root "target/settlement/$RunName"
if(Test-Path -LiteralPath $work){throw 'Use a fresh payment run name'}
New-Item -ItemType Directory -Path $work -Force | Out-Null
$names=@('B_DATABASE_ENABLED','B_DATABASE_URL','B_DATABASE_USERNAME','B_DATABASE_PASSWORD','B_DATABASE_SCOPE','B_MIGRATION_USERNAME','B_MIGRATION_PASSWORD','B_IDENTITY_ORIGIN','B_IDENTITY_SECURE_COOKIES','B_IDENTITY_KEY_ID','B_IDENTITY_PRIVATE_KEY_FILE','B_IDENTITY_PUBLIC_KEY_FILE','B_PRODUCT_EVENT_PRODUCER','B_PRODUCT_EVENT_SOURCE','B_PRODUCT_EVENT_CHANNEL','B_PAYMENT_WORK')
$previous=@{};foreach($name in $names){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
Push-Location $root
try{
 if(-not $SkipBuild){Invoke-BMaven -JavaHome $jdk.Home -Arguments @('-B','package')}
 & (Join-Path $root 'scripts/provision-b-database.ps1') -TestDatabase -JavaHome $jdk.Home -SkipBuild *> "$work/provision.log"
 Copy-Item target/database/migrate.txt "$work/migrate.txt"
 Copy-Item target/database/verify.txt "$work/permissions.txt"
 $c=Import-Clixml -LiteralPath (Join-Path $root '.local/b02-test-database.credentials.xml')
 Restore-BEnvironmentVariable B_DATABASE_URL $c.Url
 Restore-BEnvironmentVariable B_DATABASE_USERNAME $c.Runtime.UserName
 Restore-BEnvironmentVariable B_DATABASE_PASSWORD $c.Runtime.GetNetworkCredential().Password
 Restore-BEnvironmentVariable B_DATABASE_SCOPE $c.Scope
 Restore-BEnvironmentVariable B_DATABASE_ENABLED true
 Restore-BEnvironmentVariable B_MIGRATION_USERNAME $null
 Restore-BEnvironmentVariable B_MIGRATION_PASSWORD $null
 Restore-BEnvironmentVariable B_IDENTITY_ORIGIN 'http://127.0.0.1:5173'
 Restore-BEnvironmentVariable B_IDENTITY_SECURE_COOKIES false
 Restore-BEnvironmentVariable B_IDENTITY_KEY_ID b02-test
 Restore-BEnvironmentVariable B_IDENTITY_PRIVATE_KEY_FILE (Join-Path $root '.local/b02-test-keys/private.pem')
 Restore-BEnvironmentVariable B_IDENTITY_PUBLIC_KEY_FILE (Join-Path $root '.local/b02-test-keys/public.pem')
 Restore-BEnvironmentVariable B_PRODUCT_EVENT_PRODUCER 'zj-market'
 Restore-BEnvironmentVariable B_PRODUCT_EVENT_SOURCE s01
 Restore-BEnvironmentVariable B_PRODUCT_EVENT_CHANNEL c01
 Restore-BEnvironmentVariable B_PAYMENT_WORK $work
 $jar=Join-Path $root 'zj-market-verification/target/zj-market-verification.jar'
 foreach($mode in @('verify','recover')){& $jdk.Java -jar $jar --settlement $mode *> "$work/$mode.log";if($LASTEXITCODE -ne 0){throw "Payment $mode failed; see ignored report"};Get-Content "$work/$mode.txt"}
}finally{foreach($name in $names){Restore-BEnvironmentVariable $name $previous[$name]};Pop-Location}
