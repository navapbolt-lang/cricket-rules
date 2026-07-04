# Cricket Rules AI — Windows Deployment Script
# Run this on a Windows server with Docker Desktop installed

param(
    [string]$Domain = "cricketrules.ai",
    [string]$Email = "admin@cricketrules.ai",
    [switch]$SkipSSL,
    [switch]$Ingest
)

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot

Write-Host "=== Cricket Rules AI Deployment ===" -ForegroundColor Cyan
Write-Host "Domain: $Domain" -ForegroundColor Yellow

# 1. Check Docker
try {
    $ver = docker --version
    Write-Host "[OK] Docker: $ver" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Docker not found. Install Docker Desktop first." -ForegroundColor Red
    exit 1
}

# 2. Check Docker Compose
try {
    $compose = docker compose version
    Write-Host "[OK] Docker Compose: $compose" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Docker Compose not found." -ForegroundColor Red
    exit 1
}

# 3. Set up .env
$ENV_FILE = Join-Path $ROOT ".env"
if (-not (Test-Path $ENV_FILE)) {
    $EXAMPLE = Join-Path $ROOT "deployment.env.example"
    if (Test-Path $EXAMPLE) {
        Copy-Item $EXAMPLE $ENV_FILE
        $key1 = -join ((65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object { [char]$_ })
        $key2 = -join ((65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object { [char]$_ })
        (Get-Content $ENV_FILE) -replace "GEMINI_API_KEY=.*", "GEMINI_API_KEY=$env:GEMINI_API_KEY" `
            -replace "ADMIN_API_KEY=.*", "ADMIN_API_KEY=$key1" `
            -replace "JWT_SECRET=.*", "JWT_SECRET=$key2" `
            -replace "DOMAIN_NAME=.*", "DOMAIN_NAME=$Domain" `
            -replace "ADMIN_EMAIL=.*", "ADMIN_EMAIL=$Email" `
            | Set-Content $ENV_FILE
        Write-Host "[OK] Created .env from template" -ForegroundColor Green
    }
} else {
    Write-Host "[OK] .env already exists" -ForegroundColor Green
}

# 4. Update nginx config with domain
$NGINX_CONF = Join-Path $ROOT "nginx\sites\cricket-rules.conf"
if (Test-Path $NGINX_CONF) {
    (Get-Content $NGINX_CONF) -replace "DOMAIN_NAME", $Domain | Set-Content $NGINX_CONF
    Write-Host "[OK] Updated nginx config with domain: $Domain" -ForegroundColor Green
}

# 5. Pull images and build
Write-Host "[BUILD] Building and pulling Docker images..." -ForegroundColor Yellow
Set-Location $ROOT
docker compose pull qdrant redis postgres nginx certbot
docker compose build app
Write-Host "[OK] Build complete" -ForegroundColor Green

# 6. Start services (without SSL first)
Write-Host "[START] Starting services..." -ForegroundColor Yellow
docker compose up -d qdrant redis postgres
Write-Host "[WAIT] Waiting for Qdrant to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
docker compose up -d app
Start-Sleep -Seconds 10

# 7. Ingest PDFs if requested
if ($Ingest) {
    Write-Host "[INGEST] Running PDF ingestion..." -ForegroundColor Yellow
    docker compose run --rm ingest
    Write-Host "[OK] Ingestion complete" -ForegroundColor Green
}

# 8. Start nginx
docker compose up -d nginx
Write-Host "[OK] nginx started" -ForegroundColor Green

# 9. SSL via Certbot (unless skipped)
if (-not $SkipSSL) {
    Write-Host "[SSL] Requesting Let's Encrypt certificate..." -ForegroundColor Yellow
    docker compose run --rm certbot certonly --webroot -w /var/www/certbot `
        -d $Domain --email $Email --agree-tos --non-interactive
    Write-Host "[OK] SSL certificate obtained" -ForegroundColor Green
    docker compose restart nginx
}

Write-Host "" -ForegroundColor Cyan
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host "API: https://$Domain/api/v1/health" -ForegroundColor Cyan
Write-Host "Widget JS: https://$Domain/widget/embed.js" -ForegroundColor Cyan
Write-Host "Admin: https://$Domain/admin/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  View logs:  docker compose logs -f app" -ForegroundColor Gray
Write-Host "  Ingest PDFs: docker compose run --rm ingest" -ForegroundColor Gray
Write-Host "  Stop:        docker compose down" -ForegroundColor Gray
