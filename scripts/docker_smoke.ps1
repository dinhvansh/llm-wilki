param(
  [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$composeArgs = @("compose", "up", "-d")
if (-not $SkipBuild) {
  $composeArgs += "--build"
}
$composeArgs += "--force-recreate"
$composeArgs += @("postgres", "redis", "minio", "openflowkit-signaling", "openflowkit", "backend", "worker", "frontend")

docker @composeArgs

function Wait-HttpOk($Url, $Name) {
  $deadline = (Get-Date).AddMinutes(3)
  do {
    try {
      $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
        Write-Host "$Name OK $($response.StatusCode)"
        return
      }
    } catch {
      Start-Sleep -Seconds 5
    }
  } while ((Get-Date) -lt $deadline)
  throw "$Name did not become ready at $Url"
}

Wait-HttpOk "http://localhost:18000/health" "Backend health"
Wait-HttpOk "http://localhost:18000/ready" "Backend readiness"
Wait-HttpOk "http://localhost:3100" "Frontend"
Wait-HttpOk "http://localhost:3045" "OpenFlowKit"
Wait-HttpOk "http://localhost:19000/minio/health/live" "MinIO"

$login = Invoke-RestMethod -Uri "http://localhost:18000/api/auth/login" -Method Post -ContentType "application/json" -Body '{"email":"admin@local.test","password":"admin123"}'
if (-not $login.token) {
  throw "Expected auth login token"
}
$authHeaders = @{ Authorization = "Bearer $($login.token)" }
$me = Invoke-RestMethod -Uri "http://localhost:18000/api/auth/me" -Method Get -Headers $authHeaders
if ($me.role -ne "admin") {
  throw "Expected dev admin auth role"
}
$collections = Invoke-RestMethod -Uri "http://localhost:18000/api/collections" -Method Get -Headers $authHeaders
if ($collections.Count -lt 1) {
  throw "Expected at least one collection"
}

$jobs = Invoke-RestMethod -Uri "http://localhost:18000/api/jobs?limit=5" -Method Get -Headers $authHeaders
$settings = Invoke-RestMethod -Uri "http://localhost:18000/api/settings" -Method Get -Headers $authHeaders
if (-not $settings) {
  throw "Expected authenticated settings response"
}

Write-Host "Docker smoke PASS. Collections=$($collections.Count), Jobs=$($jobs.Count), Auth=$($me.role), OpenFlowKit=ok, MinIO=ok"
