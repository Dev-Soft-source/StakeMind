$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path "alembic.ini")) {
    throw "alembic.ini was not found. Run this script from backend/scripts."
}

alembic upgrade head
