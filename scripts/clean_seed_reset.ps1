param(
  [switch]$Apply
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Push-Location $Root
try {
  if (-not $Apply) {
    Write-Host "Dry run only. This will run: docker compose down -v; docker compose up -d --build"
    Write-Host "Pass -Apply to reset Docker volumes and reseed from application bootstrap."
    exit 0
  }

  docker compose down -v
  if ($LASTEXITCODE -ne 0) { throw "docker compose down -v failed" }
  docker compose up -d --build postgres redis minio drawio backend worker frontend
  if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }
  powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild
  Write-Host "Clean seed reset PASS"
}
finally {
  Pop-Location
}
