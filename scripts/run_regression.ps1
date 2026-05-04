param(
  [switch]$SkipDocker,
  [switch]$SkipE2E
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Push-Location $Root
try {
  python backend\scripts\test_phase16.py
  python backend\scripts\test_phase17.py
  python backend\scripts\test_phase19.py
  python backend\scripts\test_phase20.py
  python backend\scripts\test_phase21.py
  python backend\scripts\test_phase23.py
  python backend\scripts\test_phase24.py
  python backend\scripts\test_phase25.py
  python backend\scripts\test_phase26.py
  python backend\scripts\test_phase27.py
  python backend\scripts\test_phase28.py
  python backend\scripts\test_phase29.py
  python backend\scripts\test_phase30.py
  python backend\scripts\test_phase31.py
  python backend\scripts\test_phase32.py
  python backend\scripts\test_phase33.py
  python backend\scripts\test_ask_history.py
  python backend\scripts\test_ask_image_order.py
  python backend\scripts\benchmark_retrieval.py
  python backend\scripts\evaluate_quality.py
  python -m compileall backend\app backend\migrations backend\scripts
  npm --prefix llm-wiki run build

  if (-not $SkipDocker) {
    docker compose up -d --build postgres redis backend worker frontend drawio
    powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild
  }

  if (-not $SkipE2E) {
    powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1
  }
}
finally {
  Pop-Location
}
