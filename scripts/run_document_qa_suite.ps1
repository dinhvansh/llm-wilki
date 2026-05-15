param(
  [switch]$SkipDocker,
  [switch]$SkipE2E,
  [switch]$SkipFrontendBuild,
  [switch]$SkipLocalRegression
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BackendPython = Join-Path $Root "backend\.venv\Scripts\python.exe"
$ReportJson = Join-Path $Root "backend\evals\last_document_qa_suite.json"
$ReportMd = Join-Path $Root "backend\evals\last_document_qa_suite.md"
$Results = New-Object System.Collections.Generic.List[object]

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
  throw "Backend virtual environment was not found at $BackendPython. Run scripts\setup_local_backend.ps1 first."
}

function Add-Step {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Name,
    [Parameter(Mandatory = $true)]
    [scriptblock]$Action,
    [string]$Category = "general"
  )

  $startedAt = Get-Date
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  try {
    & $Action
    $sw.Stop()
    $Results.Add([pscustomobject]@{
      name = $Name
      category = $Category
      status = "passed"
      durationSeconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
      startedAt = $startedAt.ToString("o")
      finishedAt = (Get-Date).ToString("o")
      error = $null
    }) | Out-Null
  }
  catch {
    $sw.Stop()
    $Results.Add([pscustomobject]@{
      name = $Name
      category = $Category
      status = "failed"
      durationSeconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
      startedAt = $startedAt.ToString("o")
      finishedAt = (Get-Date).ToString("o")
      error = $_.Exception.Message
    }) | Out-Null
    throw
  }
}

function Write-Report {
  $passed = @($Results | Where-Object { $_.status -eq "passed" }).Count
  $failed = @($Results | Where-Object { $_.status -eq "failed" }).Count
  $payload = [ordered]@{
    success = ($failed -eq 0)
    generatedAt = (Get-Date).ToString("o")
    totalSteps = $Results.Count
    passedSteps = $passed
    failedSteps = $failed
    steps = $Results
  }
  $payload | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $ReportJson

  $lines = @()
  $lines += "# Document QA Automated Suite"
  $lines += ""
  $lines += "- Success: $($payload.success)"
  $lines += "- Generated at: $($payload.generatedAt)"
  $lines += "- Passed: $passed"
  $lines += "- Failed: $failed"
  $lines += ""
  $lines += "| Step | Category | Status | Duration (s) |"
  $lines += "|---|---|---|---:|"
  foreach ($item in $Results) {
    $lines += "| $($item.name) | $($item.category) | $($item.status) | $($item.durationSeconds) |"
    if ($item.error) {
      $lines += ""
      $lines += "Error for **$($item.name)**: $($item.error)"
      $lines += ""
    }
  }
  $lines | Set-Content -Encoding UTF8 $ReportMd
}

Push-Location $Root
try {
  $Python = Get-BackendPython

  Add-Step "setup_local_backend" { Invoke-Checked "powershell" @("-ExecutionPolicy", "Bypass", "-File", ".\scripts\setup_local_backend.ps1") } "environment"
  Add-Step "pip_check" { Invoke-Checked $Python @("-m", "pip", "check") } "environment"

  Add-Step "test_phase28" { Invoke-Checked $Python @("backend\scripts\test_phase28.py") } "ocr"

  foreach ($script in @(
    "test_phase33.py",
    "test_phase34.py",
    "test_phase35.py",
    "test_phase36.py",
    "test_phase37.py",
    "test_phase38.py",
    "test_phase40.py",
    "test_phase41.py",
    "test_phase42.py",
    "test_phase43.py",
    "test_phase44.py",
    "test_phase45.py",
    "test_phase46.py",
    "test_phase47.py",
    "test_phase48.py",
    "test_phase49.py",
    "test_phase50.py",
    "test_phase51.py",
    "test_phase52.py",
    "test_phase53.py",
    "test_phase54.py",
    "test_phase55.py",
    "test_ask_history.py",
    "test_ask_image_order.py"
  )) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($script)
    Add-Step $name { Invoke-Checked $Python @("backend\scripts\$script") } "targeted"
  }

  Add-Step "benchmark_retrieval" { Invoke-Checked $Python @("backend\scripts\benchmark_retrieval.py") } "quality"
  Add-Step "evaluate_quality_full" { Invoke-Checked $Python @("backend\scripts\evaluate_quality.py") } "quality"
  Add-Step "evaluate_quality_followup" { Invoke-Checked $Python @("backend\scripts\evaluate_quality.py", "--tag", "followup") } "quality"
  Add-Step "evaluate_quality_conflict" { Invoke-Checked $Python @("backend\scripts\evaluate_quality.py", "--tag", "conflict") } "quality"
  Add-Step "evaluate_quality_notebook" { Invoke-Checked $Python @("backend\scripts\evaluate_quality.py", "--tag", "notebook") } "quality"
  Add-Step "compare_quality_runs_eval" { Invoke-Checked $Python @("backend\scripts\compare_quality_runs.py", "--run-type", "eval") } "quality"
  Add-Step "compileall" { Invoke-Checked $Python @("-m", "compileall", "backend\app", "backend\migrations", "backend\scripts") } "environment"

  if (-not $SkipFrontendBuild) {
    Add-Step "frontend_build" { npm --prefix llm-wiki run build; if ($LASTEXITCODE -ne 0) { throw "Frontend build failed with exit code ${LASTEXITCODE}" } } "frontend"
  }

  if (-not $SkipLocalRegression) {
    Add-Step "run_regression_local" { Invoke-Checked "powershell" @("-ExecutionPolicy", "Bypass", "-File", ".\scripts\run_regression.ps1", "-SkipDocker", "-SkipE2E") } "regression"
  }

  if (-not $SkipDocker) {
    Add-Step "docker_rebuild" { docker compose up -d --build --force-recreate postgres redis minio openflowkit-signaling openflowkit backend worker frontend; if ($LASTEXITCODE -ne 0) { throw "Docker rebuild failed with exit code ${LASTEXITCODE}" } } "docker"
    Add-Step "docker_smoke" { Invoke-Checked "powershell" @("-ExecutionPolicy", "Bypass", "-File", ".\scripts\docker_smoke.ps1", "-SkipBuild") } "docker"
  }

  if (-not $SkipE2E) {
    Add-Step "e2e_smoke" { Invoke-Checked "powershell" @("-ExecutionPolicy", "Bypass", "-File", ".\scripts\e2e_smoke.ps1") } "e2e"
  }
}
finally {
  Write-Report
  Pop-Location
}
