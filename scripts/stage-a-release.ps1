[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ArtifactDirectory)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$manifest=Get-Content -LiteralPath (Join-Path $root 'docs/b06-a-release-manifest.json') -Raw | ConvertFrom-Json
$releaseRoot=[IO.Path]::GetFullPath((Join-Path $root ('.local/b06-artifacts/a/'+$manifest.files[0].sha256.ToLowerInvariant())))
New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
foreach($file in $manifest.files){
    $source=Join-Path $ArtifactDirectory $file.name
    if(-not(Test-Path -LiteralPath $source -PathType Leaf)){throw "Missing release input: $($file.name)"}
    if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $file.sha256){throw "Release input hash mismatch: $($file.name)"}
}
# Validate every input before copying. Existing different files must never be overwritten.
foreach($file in $manifest.files){
    $target=Join-Path $releaseRoot $file.name
    if((Test-Path -LiteralPath $target) -and (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $file.sha256){throw "Existing frozen release differs: $($file.name)"}
}
foreach($file in $manifest.files){
    $source=Join-Path $ArtifactDirectory $file.name
    $target=Join-Path $releaseRoot $file.name
    if(-not(Test-Path -LiteralPath $target)){Copy-Item -LiteralPath $source -Destination $target}
    if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $file.sha256){throw "Frozen release verification failed: $($file.name)"}
}
Write-Output "A release verified: $($manifest.releaseId)"
Write-Output "Private artifact directory: $releaseRoot"
