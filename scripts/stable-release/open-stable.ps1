[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Root)
$ErrorActionPreference = 'Stop'
$releaseDir = Join-Path $Root 'releases\td06-stable-20261016-01'
$release = Get-Content -LiteralPath (Join-Path $releaseDir 'release.json') -Raw | ConvertFrom-Json
$private = Get-Content -LiteralPath (Join-Path $Root 'private\files-manifest.json') -Raw | ConvertFrom-Json
$caPath = Join-Path (Join-Path $Root 'private') $private.probe.'web-ca.pem'.relativePath
$cert = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($caPath)
try {
  $fingerprint = 'SHA256:' + $cert.GetCertHashString('SHA256')
  if ($fingerprint -ne $release.webCaFingerprint) { throw 'Pinned CA fingerprint mismatch' }
  $store = [System.Security.Cryptography.X509Certificates.X509Store]::new('Root','CurrentUser')
  $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
  try {
    $present = @($store.Certificates | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }).Count -gt 0
    if (-not $present) { $store.Add($cert) }
  } finally { $store.Close() }
  $state = Join-Path $Root 'state'
  $receipt = Join-Path $state 'browser-trust.json'
  if (-not (Test-Path -LiteralPath $receipt)) {
    $temp = "$receipt.tmp"
    @{ thumbprint=$cert.Thumbprint; imported=(-not $present); scope='CurrentUser/Root' } |
      ConvertTo-Json | Set-Content -LiteralPath $temp -Encoding utf8
    Move-Item -LiteralPath $temp -Destination $receipt
  }
  $edge = $release.edgeExecutable
  if (-not (Test-Path -LiteralPath $edge)) { throw 'Pinned Microsoft Edge executable missing' }
  $profile = Join-Path $state 'browser-profile'
  Start-Process -FilePath $edge -WindowStyle Normal -ArgumentList @(
    ('--user-data-dir="' + $profile + '"'),
    '--host-resolver-rules="MAP zj-market.test 127.0.0.1"',
    '--no-proxy-server',
    'https://zj-market.test'
  ) | Out-Null
  Write-Output 'Opened stable TD-06 browser profile.'
} finally { $cert.Dispose() }
