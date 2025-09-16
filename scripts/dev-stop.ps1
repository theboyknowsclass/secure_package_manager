# Development tear-down script for Windows PowerShell

Write-Host "🛑 Stopping development environment..." -ForegroundColor Yellow

# Ensure we're using the correct Docker context
Write-Host "🔧 Setting Docker context..." -ForegroundColor Yellow
docker context use default

# Stop and remove all containers
Write-Host "📦 Stopping containers..." -ForegroundColor Yellow
docker compose --env-file .env.development -f docker-compose.base.yml -f docker-compose.dev.yml down

# Force stop any remaining containers (in case some were started manually)
Write-Host "🔧 Force stopping any remaining containers..." -ForegroundColor Yellow
docker stop $(docker ps -q) 2>$null
docker rm $(docker ps -aq) 2>$null

# Remove volumes (optional - uncomment if you want to completely reset)
# Write-Host "🗑️  Removing volumes..." -ForegroundColor Yellow
# docker compose --env-file .env.development -f docker-compose.base.yml -f docker-compose.dev.yml down -v

# Remove any dangling images (optional)
# Write-Host "🧹 Cleaning up dangling images..." -ForegroundColor Yellow
# docker image prune -f

Write-Host "✅ Development environment stopped!" -ForegroundColor Green
Write-Host "💡 To start again, run: .\scripts\dev-start.ps1" -ForegroundColor Cyan
Write-Host "💡 To completely reset (including database), run: .\scripts\dev-reset.ps1" -ForegroundColor Cyan
