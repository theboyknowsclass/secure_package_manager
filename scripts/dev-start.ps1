# Development startup script for Windows PowerShell
# Fresh database every time

Write-Host "🚀 Starting development environment with fresh database..." -ForegroundColor Green

# Stop and remove all containers
Write-Host "📦 Stopping existing containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v

# Remove any existing database volumes to ensure fresh start
Write-Host "🗑️  Removing database volumes..." -ForegroundColor Yellow
docker volume rm secure_package_manager_postgres_data 2>$null
docker volume rm secure_package_manager_npm_storage 2>$null

# Start services with dev configuration
Write-Host "🔄 Starting services..." -ForegroundColor Yellow
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

Write-Host "✅ Development environment started!" -ForegroundColor Green
Write-Host "🌐 Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "🔧 API: http://localhost:5000" -ForegroundColor Cyan
Write-Host "🗄️  Database: localhost:5432" -ForegroundColor Cyan
Write-Host "🔍 Trivy: http://localhost:4954" -ForegroundColor Cyan
Write-Host "🔐 Mock IDP: http://localhost:8081" -ForegroundColor Cyan
Write-Host "📦 Mock NPM Registry: http://localhost:8080" -ForegroundColor Cyan
