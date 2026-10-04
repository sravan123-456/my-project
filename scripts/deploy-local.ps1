# Deploy DanSetu to your local Docker dev environment (branch: dev).
# Usage: .\scripts\deploy-local.ps1
# App URL: http://localhost:8080

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

Write-Host "==> DanSetu local deploy (dev)" -ForegroundColor Cyan
Write-Host "    Project: $ProjectRoot"

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "WARNING: Created .env from .env.example — set SECRET_KEY and MSG91 keys for full testing." -ForegroundColor Yellow
    } else {
        throw ".env file missing."
    }
}

$branch = (git rev-parse --abbrev-ref HEAD 2>$null)
if ($branch -and $branch -ne "dev") {
    Write-Host "NOTE: You are on branch '$branch'. Local dev workflow uses the 'dev' branch." -ForegroundColor Yellow
}

Write-Host "==> Building and starting containers..."
docker compose up --build -d

Write-Host "==> Waiting for health check..."
$healthy = $false
for ($i = 1; $i -le 24; $i++) {
    Start-Sleep -Seconds 5
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    } catch {
        Write-Host "    Attempt $i/24 — not ready yet..."
    }
}

if (-not $healthy) {
    Write-Host "ERROR: App did not become healthy. Check: docker compose logs -f" -ForegroundColor Red
    exit 1
}

Write-Host "==> Running smoke tests inside container..."
docker compose exec -T festival-app python scripts/smoke_test.py --url http://127.0.0.1:5000
if ($LASTEXITCODE -ne 0) {
    Write-Host "Smoke tests failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Local dev deploy OK." -ForegroundColor Green
Write-Host "Open: http://localhost:8080"
Write-Host "When satisfied, merge dev -> main to deploy production (GitHub Actions)."
