param(
  [string]$ApiBase = "http://localhost:18000/api",
  [string]$FrontendBase = "http://localhost:3100"
)

$ErrorActionPreference = "Stop"

function Invoke-Json($Uri, $Method = "GET", $Body = $null, $Headers = @{}) {
  $params = @{
    Uri = $Uri
    Method = $Method
    Headers = $Headers
  }
  if ($null -ne $Body) {
    $params.ContentType = "application/json"
    $params.Body = ($Body | ConvertTo-Json -Depth 10)
  }
  Invoke-RestMethod @params
}

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

Wait-HttpOk "$FrontendBase" "Frontend"
Wait-HttpOk "http://localhost:18000/ready" "Backend readiness"

$login = Invoke-Json "$ApiBase/auth/login" "POST" @{ email = "admin@local.test"; password = "admin123" }
$headers = @{ Authorization = "Bearer $($login.token)" }

$textSource = Invoke-Json "$ApiBase/sources/text" "POST" @{
  title = "Phase 18 E2E Source"
  content = "Phase 18 E2E source validates upload, queued jobs, citations, review, graph, lint, and browser route smoke. Citation accuracy and hybrid retrieval are required for grounded answers."
  sourceType = "txt"
} $headers

$jobId = $textSource.metadataJson.jobId
$deadline = (Get-Date).AddMinutes(3)
do {
  Start-Sleep -Seconds 3
  $job = Invoke-Json "$ApiBase/jobs/$jobId" "GET" $null $headers
  if ($job.status -in @("completed", "failed", "canceled")) { break }
} while ((Get-Date) -lt $deadline)
if ($job.status -ne "completed") {
  throw "Expected text ingest job to complete, got $($job.status)"
}

$source = Invoke-Json "$ApiBase/sources/$($textSource.id)" "GET" $null $headers
if ($source.parseStatus -ne "indexed") {
  throw "Expected indexed source after worker processing"
}

$affectedPages = Invoke-Json "$ApiBase/sources/$($source.id)/affected-pages" "GET" $null $headers
if ($affectedPages.Count -lt 1) {
  throw "Expected generated page for E2E source"
}
$page = $affectedPages[0]
$published = Invoke-Json "$ApiBase/pages/$($page.id)/publish" "POST" $null $headers
$unpublished = Invoke-Json "$ApiBase/pages/$($page.id)/unpublish" "POST" $null $headers
$audit = Invoke-Json "$ApiBase/pages/$($page.id)/audit" "GET" $null $headers
if ($audit.Count -lt 2) {
  throw "Expected publish/unpublish audit history"
}

$ask = Invoke-Json "$ApiBase/ask" "POST" @{ question = "What does Phase 18 validate?" } $headers
if ($ask.citations.Count -lt 1) {
  throw "Expected Ask AI citations"
}

$review = Invoke-Json "$ApiBase/review-items?pageSize=5" "GET" $null $headers
$graph = Invoke-Json "$ApiBase/graph?limit=25" "GET"
$lint = Invoke-Json "$ApiBase/lint?pageSize=5" "GET" $null $headers
if ($graph.nodes.Count -lt 1 -or $lint.summary.issueCount -lt 0) {
  throw "Expected graph and lint responses"
}

$routes = @("/", "/sources", "/sources/$($source.id)", "/pages", "/pages/$($page.slug)", "/ask", "/review", "/graph", "/lint", "/collections")
foreach ($route in $routes) {
  Wait-HttpOk "$FrontendBase$route" "Route $route"
}

Write-Host "E2E smoke PASS. Source=$($source.id), Page=$($page.slug), ReviewItems=$($review.total), GraphNodes=$($graph.nodes.Count)"
