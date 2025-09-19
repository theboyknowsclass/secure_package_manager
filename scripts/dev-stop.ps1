# Development tear-down script for Windows PowerShell
# Usage: .\dev-stop.ps1 [service_name]
# If no service is specified, stops all services

param(
    [string]$Service = ""
)

if ($Service) {
    Write-Host "🛑 Stopping development service: $Service..." -ForegroundColor Yellow
} else {
    Write-Host "🛑 Stopping development environment..." -ForegroundColor Yellow
}

# Ensure we're using the correct Docker context
Write-Host "🔧 Setting Docker context..." -ForegroundColor Yellow
docker context use default

if ($Service) {
    # Single service mode - just stop the specified service
    Write-Host "📦 Stopping service: $Service..." -ForegroundColor Yellow
    docker compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml stop $Service
    docker compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml rm -f $Service
    
    Write-Host "✅ Service '$Service' stopped!" -ForegroundColor Green
    Write-Host "💡 To start again, run: .\scripts\dev-start.ps1 $Service" -ForegroundColor Cyan
} else {
    # Full environment mode - stop all services
    # Stop and remove all containers
    Write-Host "📦 Stopping containers..." -ForegroundColor Yellow
    docker compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml down

    # Force stop any remaining containers (in case some were started manually)
    Write-Host "🔧 Force stopping any remaining containers..." -ForegroundColor Yellow
    docker stop $(docker ps -q) 2>$null
    docker rm $(docker ps -aq) 2>$null

    # Remove volumes (optional - uncomment if you want to completely reset)
    # Write-Host "🗑️  Removing volumes..." -ForegroundColor Yellow
    # docker compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml down -v

    # Remove any dangling images (optional)
    # Write-Host "🧹 Cleaning up dangling images..." -ForegroundColor Yellow
    # docker image prune -f

    Write-Host "✅ Development environment stopped!" -ForegroundColor Green
    Write-Host "💡 To start again, run: .\scripts\dev-start.ps1" -ForegroundColor Cyan
    Write-Host "💡 To completely reset (including database), run: .\scripts\dev-reset.ps1" -ForegroundColor Cyan
}
