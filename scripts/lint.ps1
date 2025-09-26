#!/usr/bin/env pwsh
# Linting script for the secure package manager backend

Write-Host "Running linting checks..." -ForegroundColor Green

# Change to backend directory
Set-Location -Path "backend"

# Run flake8 for syntax and style checking
Write-Host "Running flake8..." -ForegroundColor Yellow
python -m flake8 . --max-line-length=130 --extend-ignore=E203,W503

if ($LASTEXITCODE -ne 0) {
    Write-Host "Flake8 found issues!" -ForegroundColor Red
    $flake8Failed = $true
} else {
    Write-Host "Flake8 passed!" -ForegroundColor Green
}

# Run black for code formatting check
Write-Host "Running black (format check)..." -ForegroundColor Yellow
python -m black --check --diff .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Black found formatting issues!" -ForegroundColor Red
    $blackFailed = $true
} else {
    Write-Host "Black formatting is correct!" -ForegroundColor Green
}

# Run isort for import sorting check
Write-Host "Running isort (import check)..." -ForegroundColor Yellow
python -m isort --check-only --diff .

if ($LASTEXITCODE -ne 0) {
    Write-Host "isort found import issues!" -ForegroundColor Red
    $isortFailed = $true
} else {
    Write-Host "isort imports are correct!" -ForegroundColor Green
}

# Run mypy for type checking
Write-Host "Running mypy..." -ForegroundColor Yellow
python -m mypy .

if ($LASTEXITCODE -ne 0) {
    Write-Host "mypy found type issues!" -ForegroundColor Red
    $mypyFailed = $true
} else {
    Write-Host "mypy type checking passed!" -ForegroundColor Green
}

# Multi-line f-string check removed - was giving false positives

# Return to original directory
Set-Location -Path ".."

# Summary
Write-Host "`nLinting Summary:" -ForegroundColor Cyan
if ($flake8Failed -or $blackFailed -or $isortFailed -or $mypyFailed) {
    Write-Host "❌ Some linting checks failed!" -ForegroundColor Red
    Write-Host "Run 'scripts/fix.ps1' to automatically fix formatting issues." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "✅ All linting checks passed!" -ForegroundColor Green
    exit 0
}