[CmdletBinding()]
param([string]$ReportFile='',[string]$MainRoadmapCheckpoint='')
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if(-not $ReportFile){$ReportFile=Join-Path $root 'target/b03-delivery/audit.json'}
New-Item -ItemType Directory -Path (Split-Path $ReportFile -Parent) -Force | Out-Null
Push-Location $root
try {
$known=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach($file in @('.local/database.credentials.xml','.local/b02-test-database.credentials.xml')) {
 $data=Import-Clixml -LiteralPath $file
 foreach($item in @($data.Runtime,$data.Migration)){[void]$known.Add($item.GetNetworkCredential().Password)}
}
foreach($file in Get-ChildItem (Join-Path (Split-Path $root -Parent) 'group-buy-market/docs/dev-ops/ab-v2/.local') -File | Where-Object Extension -in '.env','.json','.yml','.yaml') {
 foreach($line in [IO.File]::ReadAllLines($file.FullName)) {
  if($line -match '(?i)(?:password|secret|private.?key|token)\w*["'']?\s*[:=]\s*["'']?([^\s"'',}]+)' -and $Matches[1].Length -ge 8){[void]$known.Add($Matches[1])}
 }
}
foreach($file in Get-ChildItem '.local' -Filter 'b03-*.credentials.xml'){
 $accounts=Import-Clixml -LiteralPath $file.FullName
 foreach($role in $accounts.Keys){[void]$known.Add($accounts[$role].GetNetworkCredential().Password)}
 & git check-ignore --quiet --no-index -- $file.FullName
 if($LASTEXITCODE -ne 0){throw 'Readiness credentials are not ignored'}
}
$names=@(& git ls-files --cached --others --exclude-standard | Sort-Object -Unique)
$hits=@();$privateKeys=@();$tokens=@();$actual=0
foreach($name in $names){
 $file=Join-Path $root $name
 if(-not(Test-Path -LiteralPath $file -PathType Leaf)){continue}
 $actual++;$content=[IO.File]::ReadAllText($file)
 if(@($known | Where-Object {$content.Contains($_)}).Count){$hits+= $name}
 if($content -match '(?s)-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\r\n]{64,}-----END (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'){$privateKeys+=$name}
 if($content -match '(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{15,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})'){$tokens+=$name}
}
$trackedIgnored=@(& git ls-files --cached --ignored --exclude-standard)
$ignoredGood=$true
foreach($file in @('.local/database.credentials.xml','.local/b02-test-database.credentials.xml','.local/b02-test-keys/private.pem','.local/b02-test-keys/public.pem','target/layout-audit.json','frontend/node_modules/','frontend/dist/')) {
 & git check-ignore --quiet --no-index -- $file
 if($LASTEXITCODE -ne 0){$ignoredGood=$false}
}
$roadmapPreserved=$null
if($MainRoadmapCheckpoint){$roadmapPreserved=(Get-FileHash (Join-Path (Split-Path $root -Parent) 'zj-market/docs/development-roadmap.md')).Hash -eq (Get-Content -LiteralPath $MainRoadmapCheckpoint).Trim();if(-not $roadmapPreserved){throw 'Main roadmap checkpoint changed.'}}
$report=[ordered]@{status='PASSED';scannedFiles=$actual;knownSecretCount=$known.Count;knownSecretMatches=$hits;completePrivateKeyMatches=$privateKeys;tokenMatches=$tokens;trackedIgnoredCount=$trackedIgnored.Count;localAndGeneratedIgnored=$ignoredGood;mainRoadmapPreserved=$roadmapPreserved;currentBranch=(& git branch --show-current);head=(& git rev-parse --short HEAD)}
if($hits.Count -or $privateKeys.Count -or $tokens.Count -or $trackedIgnored.Count -or -not $ignoredGood){$report.status='FAILED'}
$report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $ReportFile -Encoding utf8
$report | ConvertTo-Json -Depth 4
if($hits.Count -or $privateKeys.Count -or $tokens.Count -or $trackedIgnored.Count -or -not $ignoredGood){throw 'Safety audit failed'}

} finally {Pop-Location}
