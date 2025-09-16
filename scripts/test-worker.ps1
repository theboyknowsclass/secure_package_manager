# Test Worker Script for Windows PowerShell
# Tests the background worker service locally

Write-Host "🧪 Testing Background Worker Service..." -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "backend/worker.py")) {
    Write-Host "❌ Error: Please run this script from the project root directory" -ForegroundColor Red
    exit 1
}

# Set environment variables for testing
$env:FLASK_ENV = "development"
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/secure_package_manager"
$env:TRIVY_URL = "http://localhost:4954"
$env:SOURCE_REPOSITORY_URL = "https://registry.npmjs.org"

Write-Host "📋 Environment configured for testing" -ForegroundColor Yellow
Write-Host "  - Database: $env:DATABASE_URL" -ForegroundColor Cyan
Write-Host "  - Trivy: $env:TRIVY_URL" -ForegroundColor Cyan
Write-Host "  - NPM Registry: $env:SOURCE_REPOSITORY_URL" -ForegroundColor Cyan

# Change to backend directory
Set-Location backend

Write-Host "🚀 Starting worker service..." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the worker" -ForegroundColor Cyan

try {
    # Run the worker
    python worker.py
} catch {
    Write-Host "❌ Worker failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    # Return to project root
    Set-Location ..
    Write-Host "🛑 Worker stopped" -ForegroundColor Yellow
}
