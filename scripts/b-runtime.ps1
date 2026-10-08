function Restore-BEnvironmentVariable {
    param([string]$Name, [AllowNull()]$Value)
    if ($null -eq $Value) { Remove-Item -LiteralPath ('Env:' + $Name) -ErrorAction SilentlyContinue }
    else { [Environment]::SetEnvironmentVariable($Name, $Value, 'Process') }
}
# Shared, process-scoped JDK selection for B. Never change user/machine JAVA_HOME or PATH.
function Resolve-BJava {
    param([string]$JavaHome = '')
    if (-not $JavaHome) { $JavaHome = $env:B_JAVA_HOME }
    if (-not $JavaHome) { $JavaHome = 'C:/Program Files/Java/jdk-21' }
    $jdkRoot = (Resolve-Path -LiteralPath $JavaHome -ErrorAction Stop).Path
    $java = Join-Path $jdkRoot 'bin/java.exe'
    $compiler = Join-Path $jdkRoot 'bin/javac.exe'
    $release = Join-Path $jdkRoot 'release'
    foreach ($file in @($java,$compiler,$release)) {
        if (-not (Test-Path -LiteralPath $file)) { throw 'B requires a complete JDK 21 installation.' }
    }
    $metadata = Get-Content -LiteralPath $release -Raw
    if ($metadata -notmatch '(?m)^JAVA_VERSION="21(?:[.+-][^"]*)?"') {
        throw 'B requires JDK 21. Use -JavaHome or B_JAVA_HOME; leave A and global JAVA_HOME unchanged.'
    }
    $version = (& $java --version | Out-String)
    if ($LASTEXITCODE -ne 0 -or $version -notmatch '(?m)^(?:openjdk|java) 21(?:[ .+-]|$)') {
        throw 'Selected B executable does not run JDK 21.'
    }
    [pscustomobject]@{ Home = $jdkRoot; Java = $java; Version = $version.Trim() }
}
function Invoke-BMaven {
    param([Parameter(Mandatory = $true)][string]$JavaHome, [string[]]$Arguments = @('package'))
    $jdk = Resolve-BJava $JavaHome
    $maven = (Get-Command mvn -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    $previousJavaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Process')
    $previousPath = [Environment]::GetEnvironmentVariable('PATH', 'Process')
    try {
        [Environment]::SetEnvironmentVariable('JAVA_HOME', $jdk.Home, 'Process')
        [Environment]::SetEnvironmentVariable('PATH', (Join-Path $jdk.Home 'bin') + [IO.Path]::PathSeparator + $previousPath, 'Process')
        & $maven @Arguments
        if ($LASTEXITCODE -ne 0) { throw "B Maven failed with exit code $LASTEXITCODE." }
    } finally {
        Restore-BEnvironmentVariable -Name 'JAVA_HOME' -Value $previousJavaHome
        Restore-BEnvironmentVariable -Name 'PATH' -Value $previousPath
    }
}
