[CmdletBinding()]
param([string]$DockerContainer = 'mysql', [string]$JavaHome = '', [switch]$SkipBuild, [switch]$TestDatabase)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$schema = if ($TestDatabase) { 'zj_market_b02_test' } else { 'zj_market' }
$runtimeUser = if ($TestDatabase) { 'zj_market_b02_test_app' } else { 'zj_market_app' }
$migrationUser = if ($TestDatabase) { 'zj_market_b02_test_migrator' } else { 'zj_market_migrator' }
$localFile = Join-Path $root $(if ($TestDatabase) { '.local/b02-test-database.credentials.xml' } else { '.local/database.credentials.xml' })

function Invoke-AdminSql([string]$Sql) {
    # Existing development root secret stays in-container. Do not render SQL errors.
    $result = $Sql | & docker exec -i $DockerContainer sh -c 'MYSQL_PWD=$MYSQL_ROOT_PASSWORD exec mysql -uroot --batch --skip-column-names' 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'B provisioning SQL failed; check container/admin access (details withheld to protect credentials).' }
    return $result
}
function New-BPassword {
    $bytes = New-Object byte[] 32
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return (($bytes | ForEach-Object { $_.ToString('x2') }) -join '')
}
# Never adopt an unrelated existing schema or account.
$occupied = Invoke-AdminSql @"
SELECT CONCAT('schema:',SCHEMA_NAME) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='$schema';
SELECT CONCAT('account:',User,'@',Host) FROM mysql.user WHERE User IN ('$runtimeUser','$migrationUser');
"@
if (-not (Test-Path -LiteralPath $localFile)) {
    if ($occupied) { throw 'B schema/account exists without this worktree credential record; refusing to adopt or overwrite.' }
    New-Item -ItemType Directory -Path (Split-Path $localFile -Parent) -Force | Out-Null
    $runtimePassword = New-BPassword
    $migrationPassword = New-BPassword
    $credentials = [pscustomobject]@{
        Scope = $(if ($TestDatabase) { 'b02-test' } else { 'development' })
        Url = "jdbc:mysql://127.0.0.1:13306/$schema`?sslMode=DISABLED&allowPublicKeyRetrieval=true&connectTimeout=5000&socketTimeout=10000"
        Runtime = New-Object Management.Automation.PSCredential($runtimeUser, (ConvertTo-SecureString $runtimePassword -AsPlainText -Force))
        Migration = New-Object Management.Automation.PSCredential($migrationUser, (ConvertTo-SecureString $migrationPassword -AsPlainText -Force))
    }
    $credentials | Export-Clixml -LiteralPath $localFile
} else { $credentials = Import-Clixml -LiteralPath $localFile }
if ($credentials.Runtime.UserName -ne $runtimeUser -or $credentials.Migration.UserName -ne $migrationUser) {
    throw 'Unexpected credential principals.'
}
$runtimePassword = $credentials.Runtime.GetNetworkCredential().Password
$migrationPassword = $credentials.Migration.GetNetworkCredential().Password
if ($runtimePassword -notmatch '^[0-9a-f]{64}$' -or $migrationPassword -notmatch '^[0-9a-f]{64}$') { throw 'Unexpected generated credential format.' }
# No DROP/ALTER USER, no global privileges, no GRANT OPTION, no A schema writes.
$sql = @"
CREATE DATABASE IF NOT EXISTS $schema CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS '$runtimeUser'@'%' IDENTIFIED BY '$runtimePassword';
CREATE USER IF NOT EXISTS '$migrationUser'@'%' IDENTIFIED BY '$migrationPassword';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX, REFERENCES ON $schema.* TO '$migrationUser'@'%';
"@
Invoke-AdminSql $sql | Out-Null
& (Join-Path $PSScriptRoot 'database.ps1') -Mode migrate -CredentialFile $localFile -JavaHome $JavaHome -SkipBuild:$SkipBuild
foreach ($table in @('b_database_probe','b_user','b_user_role','b_login_grant','b_refresh_token','b_product','b_product_outbox','b_product_sync','b_sync_inbox','b_sync_quarantine','b_sync_audit','b_inventory_account','b_inventory_operation','b_inventory_ledger','b_purchase_confirmation','b_purchase_guard','b_market_order','b_inventory_reservation','b_trade_coordination','b_trade_attempt','b_order_operation')) {
    Invoke-AdminSql "GRANT SELECT, INSERT, UPDATE, DELETE ON $schema.$table TO '$runtimeUser'@'%';" | Out-Null
}
& (Join-Path $PSScriptRoot 'database.ps1') -Mode verify -CredentialFile $localFile -JavaHome $JavaHome -SkipBuild
Write-Host 'B independent database and account boundary: PASSED. Credentials encrypted with Windows DPAPI.'
