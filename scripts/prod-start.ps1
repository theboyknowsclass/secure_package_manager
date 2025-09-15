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

# Stop any existing containers
Write-Host "📦 Stopping existing containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Start services with production configuration
Write-Host "🔄 Starting production services..." -ForegroundColor Yellow
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

Write-Host "✅ Production environment started!" -ForegroundColor Green
Write-Host "🔧 Services are running in detached mode" -ForegroundColor Cyan
Write-Host "📊 Use 'docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f' to view logs" -ForegroundColor Cyan
