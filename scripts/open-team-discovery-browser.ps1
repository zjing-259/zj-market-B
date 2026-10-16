[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][ValidateSet('main443','candidate8445')][string]$Target,
  [switch]$StatusOnly,
  [switch]$ConfigureOnly,
  [switch]$RemoveTrust
)
$ErrorActionPreference='Stop'
if(($StatusOnly -and $ConfigureOnly) -or ($StatusOnly -and $RemoveTrust) -or ($ConfigureOnly -and $RemoveTrust)) { throw 'Choose only one action switch.' }
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if($Target -eq 'main443' -and (Test-Path -LiteralPath 'D:\Java\zj-market-stable\state\adoption.json')) {
  throw 'Main 443 handed off; use D:\Java\zj-market-stable\scripts\stable.ps1 -Action open.'
}
$legacy='D:/Java/zj-market-b-06'
$candidate=Join-Path $root 'target/team-discovery/td05_20261015_01'
$ca=if($Target -eq 'main443') { Join-Path $legacy '.local/b06/runtime/web-ca.pem' } else { Join-Path $candidate 'private/runtime/web-ca.pem' }
$port=if($Target -eq 'main443') { 443 } else { 8445 }
$origin=if($Target -eq 'main443') { 'https://zj-market.test' } else { 'https://zj-market.test:8445' }
if($StatusOnly){
  & python -B (Join-Path $root 'scripts/td06-environment.py') ready --target $Target
  if($LASTEXITCODE -ne 0){throw 'Selected environment is not ready.'}
  Write-Host ('Selected '+$Target+' at '+$origin)
  return
}
if(-not(Test-Path -LiteralPath $ca)){throw 'Selected environment CA is missing.'}
$cert=[System.Security.Cryptography.X509Certificates.X509Certificate2]::new($ca)
$receiptDir=Join-Path $root 'target/team-discovery/td06-browser'
$receipt=Join-Path $receiptDir 'trust.json'
$store=[System.Security.Cryptography.X509Certificates.X509Store]::new('Root','CurrentUser')
$store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
try{
  $present=@($store.Certificates | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }).Count -gt 0
  if($RemoveTrust){
    if(-not(Test-Path -LiteralPath $receipt)){throw 'No owned trust receipt; refusing removal.'}
    $record=Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
    if($record.thumbprint -ne $cert.Thumbprint){throw 'Certificate changed; refusing removal.'}
    if($record.imported -and $present){$store.Remove($cert)}
    Write-Host 'Owned browser trust removed; browser profiles retained.'
    return
  }
  if(-not(Test-Path -LiteralPath $receipt)){
    New-Item -ItemType Directory -Path $receiptDir -Force | Out-Null
    [ordered]@{thumbprint=$cert.Thumbprint;imported=(-not $present);scope='CurrentUser/Root';domain='zj-market.test'} |
      ConvertTo-Json | Set-Content -LiteralPath $receipt -Encoding utf8
  }else{
    $record=Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
    if($record.thumbprint -ne $cert.Thumbprint){throw 'Existing trust receipt belongs to a different CA.'}
  }
  if(-not $present){$store.Add($cert)}
  if(@($store.Certificates | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }).Count -eq 0){throw 'Selected CA trust did not persist.'}
}finally{$store.Close()}
if($ConfigureOnly){Write-Host 'Current-user project CA configured; hosts unchanged.';return}
& python -B (Join-Path $root 'scripts/td06-environment.py') ready --target $Target
if($LASTEXITCODE -ne 0){throw 'Selected environment is not ready.'}
$edge='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
if(-not(Test-Path -LiteralPath $edge)){throw 'Microsoft Edge executable missing.'}
$profile=Join-Path $receiptDir ($Target+'-profile')
Start-Process -FilePath $edge -WindowStyle Normal -ArgumentList @(
  ('--user-data-dir="'+$profile+'"'),
  '--host-resolver-rules="MAP zj-market.test 127.0.0.1"',
  '--no-proxy-server',
  $origin
) | Out-Null
Write-Host ('Opened '+$Target+' at '+$origin+' with its own browser profile.')
