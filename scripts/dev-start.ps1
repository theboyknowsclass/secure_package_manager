# Development startup script for Windows PowerShell
# Fresh database every time

Write-Host "🚀 Starting development environment with fresh database..." -ForegroundColor Green

# Stop and remove all containers
Write-Host "📦 Stopping existing containers..." -ForegroundColor Yellow
docker compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml down -v

# Remove any existing database volumes to ensure fresh start
Write-Host "🗑️  Removing database volumes..." -ForegroundColor Yellow
docker volume rm secure_package_manager_postgres_data 2>$null
docker volume rm secure_package_manager_npm_storage 2>$null

# Ensure we're using the correct Docker context
Write-Host "🔧 Setting Docker context..." -ForegroundColor Yellow
docker context use default

# Remove old images to force rebuild
Write-Host "🧹 Removing old images to force rebuild..." -ForegroundColor Yellow
docker image rm secure_package_manager-api secure_package_manager-frontend secure_package_manager-mock-idp secure_package_manager-mock-npm-registry 2>$null

# Start services with dev configuration
Write-Host "🔄 Starting services..." -ForegroundColor Yellow
docker compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml up --build -d

# Wait for services to be healthy
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check if services are running
Write-Host "🔍 Checking service status..." -ForegroundColor Yellow
$services = docker compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml ps --services
$running = docker compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml ps --services --filter "status=running"

if ($services.Count -eq $running.Count) {
    Write-Host "✅ Development environment started successfully!" -ForegroundColor Green
    Write-Host "🌐 Frontend: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "🔧 API: http://localhost:5000" -ForegroundColor Cyan
    Write-Host "🗄️  Database: localhost:5432" -ForegroundColor Cyan
    Write-Host "🔍 Trivy: http://localhost:4954" -ForegroundColor Cyan
    Write-Host "🔐 Mock IDP: http://localhost:8081" -ForegroundColor Cyan
    Write-Host "📦 Mock NPM Registry: http://localhost:8080" -ForegroundColor Cyan
} else {
    Write-Host "❌ Some services failed to start. Check logs with:" -ForegroundColor Red
    Write-Host "   docker compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml logs" -ForegroundColor Yellow
    exit 1
}
