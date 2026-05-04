param(
  [switch]$KeepImages
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Push-Location $Root
try {
  docker compose down -v
  if (-not $KeepImages) {
    docker compose build --no-cache backend worker frontend
  }
  docker compose up -d postgres redis backend worker frontend
}
finally {
  Pop-Location
}
