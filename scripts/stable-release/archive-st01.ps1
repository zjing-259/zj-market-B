param()

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$inventoryPath = Join-Path $repo 'docs\tests\st00-acceptance.json'
$outputRoot = Join-Path $repo 'target\stable-isolation\st01_20261016_01'
$imageDir = Join-Path $outputRoot 'images'
$resultPath = Join-Path $outputRoot 'archive-results.json'
$inventory = Get-Content -LiteralPath $inventoryPath -Raw | ConvertFrom-Json
if ($inventory.stage -ne 'ST-00' -or -not $inventory.runtime.allImageIdsMatchTd06Archive) {
    throw 'ST-00 image inventory is not approved'
}
if (Test-Path -LiteralPath $resultPath) { throw 'Archive results already exist; select a new batch' }

$services = @('mysql', 'redis', 'namesrv', 'broker', 'marketing-a', 'market-b', 'web')
foreach ($service in $services) {
    $container = "zj-market-b06-$service-1"
    $actual = (& docker --context desktop-linux inspect --format '{{.Image}}' $container).Trim()
    if ($LASTEXITCODE -ne 0 -or $actual -ne $inventory.runtime.images.$service) {
        throw "Running image changed for $service"
    }
}
if ($inventory.runtime.images.namesrv -ne $inventory.runtime.images.broker -or
    $inventory.runtime.images.broker -ne $inventory.runtime.stoppedAuxiliary.imageId) {
    throw 'RocketMQ service/helper images differ'
}

$images = [ordered]@{
    mysql = $inventory.runtime.images.mysql
    redis = $inventory.runtime.images.redis
    rocketmq = $inventory.runtime.images.broker
    'marketing-a' = $inventory.runtime.images.'marketing-a'
    'market-b' = $inventory.runtime.images.'market-b'
    web = $inventory.runtime.images.web
}
New-Item -ItemType Directory -Path $imageDir -Force | Out-Null
$result = [ordered]@{ batch = 'st01_20261016_01'; images = [ordered]@{} }
foreach ($role in $images.Keys) {
    $id = $images[$role]
    $tag = "zj-market-stable/$role`:td06-20261016-01"
    $archive = Join-Path $imageDir "$role.tar"
    $partial = "$archive.part"
    if ((Test-Path -LiteralPath $archive) -or (Test-Path -LiteralPath $partial)) {
        throw "Archive already exists for $role; do not overwrite"
    }
    $existing = & docker --context desktop-linux image inspect --format '{{.Id}}' $tag 2>$null
    if ($LASTEXITCODE -eq 0 -and $existing.Trim() -ne $id) {
        throw "Stable tag already points to another image: $tag"
    }
    if ($LASTEXITCODE -ne 0) {
        & docker --context desktop-linux image tag $id $tag
        if ($LASTEXITCODE -ne 0) { throw "Image tag failed for $role" }
    }
    & docker --context desktop-linux image save --output $partial $tag
    if ($LASTEXITCODE -ne 0) { throw "Image save failed for $role; inspect partial file" }
    Move-Item -LiteralPath $partial -Destination $archive
    $hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
    $result.images[$role] = [ordered]@{
        id = $id
        tag = $tag
        archive = $archive.Replace('\', '/')
        sha256 = $hash
        bytes = (Get-Item -LiteralPath $archive).Length
    }
    Write-Output "ARCHIVED $role $id $hash"
}
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resultPath -Encoding utf8
Write-Output "ARCHIVE_RESULTS $resultPath"
