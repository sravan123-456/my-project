# Run DanSetu locally with Docker Desktop at http://localhost:8080
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not on PATH. Install Docker Desktop and try again."
}

$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker Desktop is not running. Start Docker Desktop, then run this script again."
}

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example"
    } else {
        Write-Error ".env file missing."
    }
}

Write-Host "Building and starting containers (local overrides)..."
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build -d

Write-Host ""
Write-Host "Local app: http://localhost:8080"
Write-Host "Health:    http://localhost:8080/health"
Write-Host "Logs:      docker compose -f docker-compose.yml -f docker-compose.local.yml logs -f festival-app"
