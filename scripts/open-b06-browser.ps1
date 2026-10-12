[CmdletBinding()]
param([switch]$ConfigureOnly,[switch]$RemoveTrust)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ca=Join-Path $root '.local/b06/runtime/web-ca.pem'
$control=Join-Path $root '.local/b06/control'
$receipt=Join-Path $control 'browser-trust.json'
$cert=[System.Security.Cryptography.X509Certificates.X509Certificate2]::new($ca)
if($RemoveTrust){
 if(-not(Test-Path $receipt)){throw 'No owned trust receipt; refusing removal'}
 $record=Get-Content $receipt -Raw|ConvertFrom-Json
 if($record.thumbprint -ne $cert.Thumbprint){throw 'Certificate changed; refusing removal'}
 if($record.imported){$target='Cert:/CurrentUser/Root/'+$record.thumbprint;if(Test-Path $target){Remove-Item -LiteralPath $target}}
 Write-Host 'Owned browser trust removed; browser data retained.'
 exit
}
$present=Test-Path ('Cert:/CurrentUser/Root/'+$cert.Thumbprint)
if(-not(Test-Path $receipt)){
 [ordered]@{thumbprint=$cert.Thumbprint;subject=$cert.Subject;imported=(-not $present);scope='CurrentUser/Root';domain='zj-market.test';resolution='dedicated Edge profile only; hosts unchanged'}|ConvertTo-Json|Set-Content $receipt
}
if(-not $present){Import-Certificate -FilePath $ca -CertStoreLocation Cert:/CurrentUser/Root|Out-Null}
if(-not(Test-Path ('Cert:/CurrentUser/Root/'+$cert.Thumbprint))){throw 'Trust import did not persist'}
if($ConfigureOnly){Write-Host 'Current-user HTTPS trust configured; hosts unchanged.';exit}
$edge='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
if(-not(Test-Path $edge)){throw 'Microsoft Edge executable missing'}
$profile=Join-Path $root '.local/b06/browser-profile'
Start-Process -FilePath $edge -WindowStyle Normal -ArgumentList @('--user-data-dir="'+$profile+'"','--host-resolver-rules="MAP zj-market.test 127.0.0.1"','--no-proxy-server','https://zj-market.test')|Out-Null
Write-Host 'Opened the dedicated local marketplace browser.'
