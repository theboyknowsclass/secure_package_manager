# Production complete reset script for Windows PowerShell
# Removes everything including database - USE WITH CAUTION!

Write-Host "⚠️  WARNING: This will completely reset the production environment!" -ForegroundColor Red
Write-Host "⚠️  All data including the database will be permanently deleted!" -ForegroundColor Red
Write-Host ""

# Confirmation prompt
$confirmation = Read-Host "Are you sure you want to continue? Type 'RESET' to confirm"
if ($confirmation -ne "RESET") {
    Write-Host "❌ Operation cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host "🔄 Completely resetting production environment..." -ForegroundColor Yellow

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

# Stop and remove all containers and volumes
Write-Host "📦 Stopping containers and removing volumes..." -ForegroundColor Yellow
docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml down -v

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

Write-Host "✅ Production environment completely reset!" -ForegroundColor Green
Write-Host "💡 To start fresh, run: .\scripts\prod-start.ps1" -ForegroundColor Cyan
Write-Host "⚠️  Remember: You'll need to restore any production data from backups!" -ForegroundColor Red
