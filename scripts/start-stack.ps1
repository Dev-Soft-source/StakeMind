param(
  [switch]$Build
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

$composeArgs = @("compose", "up")
if ($Build) {
  $composeArgs += "--build"
}

docker @composeArgs
