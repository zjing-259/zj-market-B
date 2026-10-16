[CmdletBinding()]
param(
    [string]$ARoot = 'D:/Java/group-buy-market',
    [string]$Java8Home = 'D:/Dev_tools/2.environment/jdk/jdk8',
    [string]$Java21Home = 'C:/Program Files/Java/jdk-21',
    [Parameter(Mandatory)][string]$Baseline,
    [Parameter(Mandatory)][string]$RunName
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if ($RunName -notmatch '^td00-[a-zA-Z0-9-]+$') { throw 'Use a fresh td00 run name' }
$work = Join-Path $root "target/team-discovery/$RunName"
if (Test-Path -LiteralPath $work) { throw 'Preserve old evidence; choose a fresh RunName' }
New-Item -ItemType Directory -Path $work | Out-Null
$previousJava = $env:JAVA_HOME
$previousPath = $env:PATH
function Require-Exit([string]$name) { if ($LASTEXITCODE -ne 0) { throw "$name failed; see $work" } }
try {
    $env:JAVA_HOME = $Java8Home
    $env:PATH = "$Java8Home/bin;$previousPath"
    Push-Location $ARoot
    try {
        python -B docs/dev-ops/ab-v2/generate-contract.py --check
        Require-Exit 'Contract generator check'
        & mvn -B -o -pl group-buy-market-contract -am package -DskipTests '-Dmaven.jar.forceCreation=true' *> "$work/build-1.log"
        Require-Exit 'Contract build'
        $jar = Join-Path $ARoot 'group-buy-market-contract/target/group-buy-market-contract-1.1.0-td.1.jar'
        Copy-Item -LiteralPath $jar -Destination "$work/contract.jar"
        & mvn -B -o -pl group-buy-market-contract -am package -DskipTests '-Dmaven.jar.forceCreation=true' *> "$work/build-2.log"
        Require-Exit 'Repeated package'
        if ((Get-FileHash $jar).Hash -ne (Get-FileHash "$work/contract.jar").Hash) { throw 'Repeated package bytes differ' }
    } finally { Pop-Location }
    Push-Location $root
    try {
        $classes = Join-Path $work 'check-classes'
        New-Item -ItemType Directory -Path $classes | Out-Null
        $libs = Join-Path $Baseline 'check-libs/*'
        $cp = "$jar;$libs"
        & "$Java8Home/bin/javac.exe" -encoding UTF-8 -cp $cp -d $classes docs/tests/td00/ContractCheck.java *> "$work/javac.log"
        Require-Exit 'Java8 contract harness compilation'
        foreach ($jdk in @($Java8Home,$Java21Home)) {
            $label = if ($jdk -eq $Java8Home) { 'java8' } else { 'java21' }
            & "$jdk/bin/java.exe" -cp "$classes;$cp" ContractCheck "$Baseline/artifacts/a-b06/contract.jar" $jar "$ARoot/docs/schemas/team-discovery-v1.examples.json" *> "$work/$label.log"
            Require-Exit $label
        }
        python -B docs/tests/validate-td00-contract.py --a-root $ARoot --schema-libs "$ARoot/docs/dev-ops/ab-v2/.local/schema-validator" --baseline $Baseline --output "$work/static-checks.json"
        Require-Exit 'Schema, cursor and protected source checks'
        $summary = @{ stage='TD-00'; status='PASSED_CONTRACT_BASELINE'; contractVersion='1.1.0-td.1'; contractSha256=(Get-FileHash $jar).Hash; repeatPackageIdentical=$true; java8=$true; java21=$true; oldTypesCompared=36; runtimeDiscoveryTested=$false }
        $summary | ConvertTo-Json | Set-Content -Encoding utf8 "$work/acceptance.json"
        Write-Output "PASS TD-00 contract baseline: $work"
    } finally { Pop-Location }
} finally { $env:JAVA_HOME=$previousJava; $env:PATH=$previousPath }
