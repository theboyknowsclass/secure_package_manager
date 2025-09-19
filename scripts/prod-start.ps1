# Production startup script for Windows PowerShell

Write-Host "🚀 Starting production environment..." -ForegroundColor Green

# Check for required environment variables
if (-not $env:POSTGRES_PASSWORD) {
    Write-Host "❌ Error: POSTGRES_PASSWORD environment variable is required" -ForegroundColor Red
    exit 1
}

if (-not $env:ADFS_ENTITY_ID -or -not $env:ADFS_SSO_URL) {
    Write-Host "❌ Error: ADFS_ENTITY_ID and ADFS_SSO_URL environment variables are required" -ForegroundColor Red
    exit 1
}

# Ensure we're using the correct Docker context
Write-Host "🔧 Setting Docker context..." -ForegroundColor Yellow
docker context use default

# Stop any existing containers
Write-Host "📦 Stopping existing containers..." -ForegroundColor Yellow
docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml down

# Start services with production configuration
Write-Host "🔄 Starting production services..." -ForegroundColor Yellow
docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml up -d --build

# Wait for services to be healthy
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Check if services are running
Write-Host "🔍 Checking service status..." -ForegroundColor Yellow
$services = docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml ps --services
$running = docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml ps --services --filter "status=running"

if ($services.Count -eq $running.Count) {
    Write-Host "✅ Production environment started successfully!" -ForegroundColor Green
    Write-Host "🔧 Services are running in detached mode" -ForegroundColor Cyan
    Write-Host "📊 Use 'docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml logs -f' to view logs" -ForegroundColor Cyan
} else {
    Write-Host "❌ Some services failed to start. Check logs with:" -ForegroundColor Red
    Write-Host "   docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml logs" -ForegroundColor Yellow
    exit 1
}
