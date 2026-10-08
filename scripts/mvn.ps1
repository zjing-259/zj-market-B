[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$JavaHome = '',
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)][string[]]$MavenArguments = @('package')
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'b-runtime.ps1')
$jdk = Resolve-BJava $JavaHome
Push-Location (Join-Path $PSScriptRoot '..')
try { Invoke-BMaven -JavaHome $jdk.Home -Arguments $MavenArguments }
finally { Pop-Location }
