[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateSet('status','ready','start','stop','open')][string]$Action)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$release = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'release.json') -Raw | ConvertFrom-Json
$python = $release.pythonExecutable
if (-not (Test-Path -LiteralPath $python)) { throw 'Pinned Python executable missing' }
& $python -B (Join-Path $PSScriptRoot 'controller.py') $Action --root $root
if ($LASTEXITCODE -ne 0) { throw "Stable $Action failed; see the sanitized error above" }
