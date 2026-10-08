[CmdletBinding()]
param([string]$JavaHome='', [string]$DatabaseCredentialFile='', [switch]$TestDatabase, [switch]$SkipBuild, [int]$Port=18092)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
if(-not $DatabaseCredentialFile -and -not $env:B_DATABASE_URL){
    $DatabaseCredentialFile=Join-Path $root $(if($TestDatabase){'.local/b02-test-database.credentials.xml'}else{'.local/database.credentials.xml'})
}
foreach($name in @('B_PRODUCT_EVENT_PRODUCER','B_PRODUCT_EVENT_SOURCE','B_PRODUCT_EVENT_CHANNEL','B_IDENTITY_ORIGIN','B_IDENTITY_KEY_ID','B_IDENTITY_PRIVATE_KEY_FILE','B_IDENTITY_PUBLIC_KEY_FILE')){
    if(-not[Environment]::GetEnvironmentVariable($name,'Process')){throw "Supply external $name before starting identity."}
}
if($TestDatabase -and -not $DatabaseCredentialFile -and ($env:B_DATABASE_URL -notmatch '^jdbc:mysql://[^/]+/zj_market_b02_test(?:\?.*)?$' -or $env:B_DATABASE_USERNAME -ne 'zj_market_b02_test_app')){throw 'Explicit isolated B test database required.'}
& (Join-Path $PSScriptRoot 'start-b.ps1') -JavaHome $JavaHome -SkipBuild:$SkipBuild -DatabaseCredentialFile $DatabaseCredentialFile -DatabaseScope $(if($TestDatabase){'b02-test'}else{'development'}) -ApplicationArguments @('--b.identity.enabled=true','--b.trial.enabled=false','--b.product.enabled=true','--b.sync.enabled=true','--b.infrastructure.rpc.enabled=true','--b.infrastructure.mq.enabled=true',"--server.port=$Port")
