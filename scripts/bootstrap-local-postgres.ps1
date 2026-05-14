param(
    [string]$PostgresUser = "postgres",
    [string]$PostgresDatabase = "postgres",
    [string]$PsqlPath = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path $PsqlPath)) {
    throw "psql was not found at '$PsqlPath'. Install PostgreSQL or pass -PsqlPath."
}

$securePassword = Read-Host "Enter the password for PostgreSQL user '$PostgresUser'" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

$env:PGPASSWORD = $plainPassword
try {
    & $PsqlPath -U $PostgresUser -d $PostgresDatabase -v ON_ERROR_STOP=1 -f "scripts/init-local-postgres.sql"
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "Created or updated role/database stakemind. Set DATABASE_URL in .env to match your PostgreSQL user (see .env.example)."
