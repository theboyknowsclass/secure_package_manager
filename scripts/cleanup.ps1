# Complete cleanup script for Windows PowerShell
# Removes all project-related Docker resources

Write-Host "🧹 Complete Docker cleanup for Secure Package Manager..." -ForegroundColor Yellow

# Stop all containers
Write-Host "📦 Stopping all containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v 2>$null
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down -v 2>$null

# Remove all project-related volumes
Write-Host "🗑️  Removing all volumes..." -ForegroundColor Yellow
docker volume rm secure_package_manager_postgres_data 2>$null
docker volume rm secure_package_manager_npm_storage 2>$null
docker volume rm secure_package_manager_package_cache 2>$null
docker volume rm secure_package_manager_trivy_cache 2>$null

# Remove project images
Write-Host "🖼️  Removing project images..." -ForegroundColor Yellow
$images = docker images | Select-String "secure_package_manager" | ForEach-Object { ($_ -split '\s+')[2] }
if ($images) {
    $images | ForEach-Object { docker rmi -f $_ 2>$null }
}

# Clean up Docker system
Write-Host "🧹 Cleaning up Docker system..." -ForegroundColor Yellow
docker system prune -f
docker builder prune -f

Write-Host "✅ Complete cleanup finished!" -ForegroundColor Green
Write-Host "💡 All Secure Package Manager Docker resources have been removed." -ForegroundColor Cyan
Write-Host "💡 To start fresh, run: .\scripts\dev-start.ps1" -ForegroundColor Cyan
