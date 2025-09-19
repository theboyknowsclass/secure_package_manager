#!/usr/bin/env pwsh
# Auto-fix script for the secure package manager backend

Write-Host "Running auto-fix for formatting issues..." -ForegroundColor Green

# Change to backend directory
Set-Location -Path "backend"

# Run black to fix formatting
Write-Host "Running black (auto-format)..." -ForegroundColor Yellow
python -m black .

if ($LASTEXITCODE -eq 0) {
    Write-Host "Black formatting applied!" -ForegroundColor Green
} else {
    Write-Host "Black formatting failed!" -ForegroundColor Red
}

# Run isort to fix import sorting
Write-Host "Running isort (auto-fix imports)..." -ForegroundColor Yellow
python -m isort .

if ($LASTEXITCODE -eq 0) {
    Write-Host "isort import sorting applied!" -ForegroundColor Green
} else {
    Write-Host "isort import sorting failed!" -ForegroundColor Red
}

# Return to original directory
Set-Location -Path ".."

Write-Host "Auto-fix completed!" -ForegroundColor Green
Write-Host "Note: Multi-line f-string issues need to be fixed manually." -ForegroundColor Yellow
