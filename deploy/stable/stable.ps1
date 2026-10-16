[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateSet('status','ready','start','stop','open')][string]$Action)
$ErrorActionPreference = 'Stop'
$releaseScript = Join-Path $PSScriptRoot '..\releases\td06-stable-20261016-01\stable.ps1'
if (-not (Test-Path -LiteralPath $releaseScript)) { throw 'Stable release entry missing' }
& $releaseScript -Action $Action
if ($LASTEXITCODE -ne 0) { throw "Stable $Action failed" }
