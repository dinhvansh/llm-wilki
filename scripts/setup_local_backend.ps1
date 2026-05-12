$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $root "backend"
$venvDir = Join-Path $backendDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\\python.exe"
$requirements = Join-Path $backendDir "requirements.txt"
$localTessdata = Join-Path $backendDir ".local\\tessdata"
$tesseractExe = "C:\Program Files\Tesseract-OCR\tesseract.exe"

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

function Ensure-Venv {
  if (-not (Test-Path $venvPython)) {
    Write-Host "Creating backend virtual environment..."
    Invoke-Checked "python" @("-m", "venv", $venvDir)
  }
}

function Install-BackendRequirements {
  Write-Host "Installing backend requirements into .venv..."
  Invoke-Checked $venvPython @("-m", "pip", "install", "certifi")
  Invoke-Checked $venvPython @("-m", "pip", "install", "-r", $requirements)
}

function Ensure-Tesseract {
  if (Test-Path $tesseractExe) {
    Write-Host "Tesseract already installed at $tesseractExe"
    return
  }

  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if (-not $winget) {
    throw "Tesseract is missing and winget is not available. Install Tesseract manually."
  }

  Write-Host "Installing Tesseract OCR via winget..."
  Invoke-Checked "winget" @("install", "--id", "UB-Mannheim.TesseractOCR", "--accept-source-agreements", "--accept-package-agreements", "--silent")
  if (-not (Test-Path $tesseractExe)) {
    throw "Tesseract installation finished but tesseract.exe was not found at $tesseractExe"
  }
}

function Ensure-LocalTessdata {
  New-Item -ItemType Directory -Force -Path $localTessdata | Out-Null

  $systemTessdata = Join-Path (Split-Path -Parent $tesseractExe) "tessdata"
  foreach ($name in @("eng.traineddata", "osd.traineddata")) {
    $source = Join-Path $systemTessdata $name
    $target = Join-Path $localTessdata $name
    if ((Test-Path $source) -and -not (Test-Path $target)) {
      Copy-Item $source $target -Force
    }
  }

  $vieTarget = Join-Path $localTessdata "vie.traineddata"
  if (-not (Test-Path $vieTarget)) {
    Write-Host "Downloading Vietnamese OCR data..."
    Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata_fast/raw/main/vie.traineddata" -OutFile $vieTarget
  }
}

Ensure-Venv
Install-BackendRequirements
Ensure-Tesseract
Ensure-LocalTessdata

Write-Host "Verifying OCR runtime..."
Push-Location $backendDir
try {
  Invoke-Checked $venvPython @("scripts\\test_phase28.py")
}
finally {
  Pop-Location
}

Write-Host ""
Write-Host "Backend local environment is ready."
Write-Host "Use:"
Write-Host "  backend\\.venv\\Scripts\\python.exe -m app.main"
Write-Host "  backend\\.venv\\Scripts\\python.exe -m app.worker"
