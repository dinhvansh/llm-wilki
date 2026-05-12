param(
  [string]$BackupDir = ".\tmp\backup-smoke"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ResolvedBackupDir = Join-Path $Root $BackupDir
New-Item -ItemType Directory -Force -Path $ResolvedBackupDir | Out-Null

function Invoke-Checked {
  param([string]$FilePath, [string[]]$Arguments)
  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
  }
}

Push-Location $Root
try {
  $pgBackupInContainer = "/tmp/llmwiki-smoke.dump"
  $pgBackupLocal = Join-Path $ResolvedBackupDir "llmwiki-smoke.dump"
  Invoke-Checked "docker" @("exec", "llm-wiki-postgres", "pg_dump", "-U", "postgres", "-d", "llmwiki", "-Fc", "-f", $pgBackupInContainer)
  Invoke-Checked "docker" @("cp", "llm-wiki-postgres:$pgBackupInContainer", $pgBackupLocal)
  if (-not (Test-Path $pgBackupLocal) -or ((Get-Item $pgBackupLocal).Length -le 0)) {
    throw "Postgres backup file was not created"
  }
  Invoke-Checked "docker" @("exec", "llm-wiki-postgres", "pg_restore", "--list", $pgBackupInContainer)

  $network = "ai-nativewikiplatform_default"
  $mcAliasArgs = @(
    "run", "--rm", "--network", $network,
    "-e", "MC_HOST_local=http://minioadmin:minioadmin@minio:9000",
    "minio/mc", "ls", "local/llm-wiki"
  )
  Invoke-Checked "docker" $mcAliasArgs

  Write-Host "Backup/restore smoke PASS. Postgres dump=$pgBackupLocal, MinIO bucket=listable"
}
finally {
  Pop-Location
}
