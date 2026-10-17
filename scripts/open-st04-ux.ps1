[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ((Split-Path $root -Leaf) -ne 'zj-market-ux') { throw 'Run this entry only from the UX worktree' }
$state = Get-Content -LiteralPath (Join-Path $root '.local/b06/control/state.json') -Raw | ConvertFrom-Json
if ($state.project -ne 'zj-market-ux' -or $state.mode -ne 'open' -or $state.phase -ne 'READY') {
  throw 'UX stack is not open and READY'
}
$caPath = Join-Path $root '.local/b06/runtime/web-ca.pem'
$cert = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($caPath)
try {
  $store = [System.Security.Cryptography.X509Certificates.X509Store]::new('Root','CurrentUser')
  $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
  try {
    if (-not @($store.Certificates | Where-Object Thumbprint -eq $cert.Thumbprint).Count) {
      $store.Add($cert)
    }
  } finally { $store.Close() }
  $edge = @(
    'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
  ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
  if (-not $edge) { throw 'Microsoft Edge executable not found' }
  $profile = Join-Path $root '.local/st04/browser-profile'
  New-Item -ItemType Directory -Path $profile -Force | Out-Null
  Start-Process -FilePath $edge -WindowStyle Normal -ArgumentList @(
    ('--user-data-dir="' + $profile + '"'),
    '--host-resolver-rules="MAP zj-market-ux.test 127.0.0.1"',
    '--no-proxy-server',
    'https://zj-market-ux.test:8446'
  ) | Out-Null
  Write-Output 'Opened isolated UX browser profile.'
} finally { $cert.Dispose() }
