# Development complete reset script for Windows PowerShell
# Removes everything including database

Write-Host "🔄 Completely resetting development environment..." -ForegroundColor Yellow

# Ensure we're using the correct Docker context
Write-Host "🔧 Setting Docker context..." -ForegroundColor Yellow
docker context use default

# Stop and remove all containers and volumes
Write-Host "📦 Stopping containers and removing volumes..." -ForegroundColor Yellow
docker compose --env-file .env.development -f docker-compose.base.yml -f docker-compose.dev.yml down -v

# Remove any dangling images and build cache
Write-Host "🧹 Cleaning up Docker resources..." -ForegroundColor Yellow
docker image prune -f
docker builder prune -f

# Remove specific volumes if they exist
Write-Host "🗑️  Removing specific volumes..." -ForegroundColor Yellow
docker volume rm secure_package_manager_postgres_data 2>$null
docker volume rm secure_package_manager_npm_storage 2>$null
docker volume rm secure_package_manager_package_cache 2>$null
docker volume rm secure_package_manager_trivy_cache 2>$null

Write-Host "✅ Development environment completely reset!" -ForegroundColor Green
Write-Host "💡 To start fresh, run: .\scripts\dev-start.ps1" -ForegroundColor Cyan
