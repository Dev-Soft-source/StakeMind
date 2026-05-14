# Logical backup of the stakemind database via docker compose (postgres service).
# Usage (from repo root): .\scripts\backup-postgres.ps1 [output-file.sql]
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$defaultDir = Join-Path $Root "backups"
if (-not (Test-Path $defaultDir)) { New-Item -ItemType Directory -Path $defaultDir | Out-Null }
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$defaultOut = Join-Path $defaultDir "postgres-$stamp.sql"
$Out = if ($args.Count -ge 1) { $args[0] } else { $defaultOut }
$parent = Split-Path $Out -Parent
if ($parent -and -not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
$p = Start-Process -FilePath "docker" `
    -ArgumentList @("compose", "exec", "-T", "postgres", "pg_dump", "-U", "stakemind", "stakemind") `
    -NoNewWindow -Wait -PassThru -RedirectStandardOutput $Out
if ($p.ExitCode -ne 0) {
    throw "docker compose pg_dump failed with exit code $($p.ExitCode)"
}
Write-Host "Wrote $Out"
