# Development tear-down script for Windows PowerShell

Write-Host "🛑 Stopping development environment..." -ForegroundColor Yellow

# Stop and remove all containers
Write-Host "📦 Stopping containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Remove volumes (optional - uncomment if you want to completely reset)
# Write-Host "🗑️  Removing volumes..." -ForegroundColor Yellow
# docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v

# Remove any dangling images (optional)
# Write-Host "🧹 Cleaning up dangling images..." -ForegroundColor Yellow
# docker image prune -f

Write-Host "✅ Development environment stopped!" -ForegroundColor Green
Write-Host "💡 To start again, run: .\scripts\dev-start.ps1" -ForegroundColor Cyan
Write-Host "💡 To completely reset (including database), run: .\scripts\dev-reset.ps1" -ForegroundColor Cyan
