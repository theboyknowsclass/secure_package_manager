# Production tear-down script for Windows PowerShell

Write-Host "🛑 Stopping production environment..." -ForegroundColor Yellow

# Stop and remove all containers
Write-Host "📦 Stopping containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

Write-Host "✅ Production environment stopped!" -ForegroundColor Green
Write-Host "💡 To start again, run: .\scripts\prod-start.ps1" -ForegroundColor Cyan
Write-Host "⚠️  Note: Database data is preserved. Use 'docker-compose down -v' to remove volumes." -ForegroundColor Yellow
