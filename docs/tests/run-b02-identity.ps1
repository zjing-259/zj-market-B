[CmdletBinding()]
param([string]$JavaHome='', [switch]$SkipBuild)
$ErrorActionPreference='Stop'
$root=Resolve-Path (Join-Path $PSScriptRoot '../..')
. (Join-Path $root 'scripts/b-runtime.ps1')
$names=@('B_IDENTITY_ORIGIN','B_IDENTITY_SECURE_COOKIES','B_IDENTITY_KEY_ID','B_IDENTITY_PRIVATE_KEY_FILE','B_IDENTITY_PUBLIC_KEY_FILE')
$previous=@{};foreach($name in $names){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
try {
    & (Join-Path $root 'scripts/provision-b-database.ps1') -TestDatabase -JavaHome $JavaHome -SkipBuild:$SkipBuild
    $keyDir=Join-Path $root '.local/b02-test-keys'
    New-Item -ItemType Directory -Path $keyDir -Force | Out-Null
    $private=Join-Path $keyDir 'private.pem';$public=Join-Path $keyDir 'public.pem'
    if(-not(Test-Path -LiteralPath $private) -and -not(Test-Path -LiteralPath $public)){
        $rsa=[Security.Cryptography.RSA]::Create(3072)
        try{[IO.File]::WriteAllText($private,$rsa.ExportPkcs8PrivateKeyPem());[IO.File]::WriteAllText($public,$rsa.ExportSubjectPublicKeyInfoPem())}finally{$rsa.Dispose()}
    }
    if(-not(Test-Path -LiteralPath $private) -or -not(Test-Path -LiteralPath $public)){throw 'Incomplete test key pair; refusing overwrite.'}
    Restore-BEnvironmentVariable B_IDENTITY_ORIGIN 'http://127.0.0.1:5173'
    Restore-BEnvironmentVariable B_IDENTITY_SECURE_COOKIES false
    Restore-BEnvironmentVariable B_IDENTITY_KEY_ID b02-test
    Restore-BEnvironmentVariable B_IDENTITY_PRIVATE_KEY_FILE $private
    Restore-BEnvironmentVariable B_IDENTITY_PUBLIC_KEY_FILE $public
    & (Join-Path $root 'scripts/identity.ps1') -Mode verify -JavaHome $JavaHome -SkipBuild
}finally{foreach($name in $names){Restore-BEnvironmentVariable $name $previous[$name]}}
