param(
  [switch]$SkipDocker,
  [switch]$SkipE2E
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BackendPython = Join-Path $Root "backend\.venv\Scripts\python.exe"

function Invoke-Checked {
  param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath,
    [string[]]$Arguments = @()
  )

  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
  }
}

function Get-BackendPython {
  if (Test-Path $BackendPython) {
    return $BackendPython
  }
  return "python"
}

Push-Location $Root
try {
  $Python = Get-BackendPython

  Invoke-Checked $Python @("backend\scripts\test_phase16.py")
  Invoke-Checked $Python @("backend\scripts\test_phase17.py")
  Invoke-Checked $Python @("backend\scripts\test_phase19.py")
  Invoke-Checked $Python @("backend\scripts\test_phase20.py")
  Invoke-Checked $Python @("backend\scripts\test_phase21.py")
  Invoke-Checked $Python @("backend\scripts\test_phase23.py")
  Invoke-Checked $Python @("backend\scripts\test_phase24.py")
  Invoke-Checked $Python @("backend\scripts\test_phase25.py")
  Invoke-Checked $Python @("backend\scripts\test_phase26.py")
  Invoke-Checked $Python @("backend\scripts\test_phase27.py")
  Invoke-Checked $Python @("backend\scripts\test_phase28.py")
  Invoke-Checked $Python @("backend\scripts\test_phase29.py")
  Invoke-Checked $Python @("backend\scripts\test_phase30.py")
  Invoke-Checked $Python @("backend\scripts\test_phase31.py")
  Invoke-Checked $Python @("backend\scripts\test_phase32.py")
  Invoke-Checked $Python @("backend\scripts\test_phase33.py")
  Invoke-Checked $Python @("backend\scripts\test_phase34.py")
  Invoke-Checked $Python @("backend\scripts\test_phase35.py")
  Invoke-Checked $Python @("backend\scripts\test_phase36.py")
  Invoke-Checked $Python @("backend\scripts\test_phase37.py")
  Invoke-Checked $Python @("backend\scripts\test_phase38.py")
  Invoke-Checked $Python @("backend\scripts\test_phase39.py")
  Invoke-Checked $Python @("backend\scripts\test_phase40.py")
  Invoke-Checked $Python @("backend\scripts\test_phase41.py")
  Invoke-Checked $Python @("backend\scripts\test_phase42.py")
  Invoke-Checked $Python @("backend\scripts\test_phase43.py")
  Invoke-Checked $Python @("backend\scripts\test_phase44.py")
  Invoke-Checked $Python @("backend\scripts\test_phase45.py")
  Invoke-Checked $Python @("backend\scripts\test_phase46.py")
  Invoke-Checked $Python @("backend\scripts\test_phase47.py")
  Invoke-Checked $Python @("backend\scripts\test_phase48.py")
  Invoke-Checked $Python @("backend\scripts\test_phase49.py")
  Invoke-Checked $Python @("backend\scripts\test_phase50.py")
  Invoke-Checked $Python @("backend\scripts\test_phase51.py")
  Invoke-Checked $Python @("backend\scripts\test_phase52.py")
  Invoke-Checked $Python @("backend\scripts\test_ask_history.py")
  Invoke-Checked $Python @("backend\scripts\test_ask_image_order.py")
  Invoke-Checked $Python @("backend\scripts\benchmark_retrieval.py")
  Invoke-Checked $Python @("backend\scripts\evaluate_quality.py")
  Invoke-Checked $Python @("-m", "compileall", "backend\app", "backend\migrations", "backend\scripts")
  npm --prefix llm-wiki run build

  if (-not $SkipDocker) {
    docker compose up -d --build --force-recreate postgres redis minio openflowkit-signaling openflowkit backend worker frontend
    powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild
  }

  if (-not $SkipE2E) {
    powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1
  }
}
finally {
  Pop-Location
}
