# Clear Package Cache Script
# Removes all packages from the package cache volume

Write-Host "🧹 Clearing package cache..." -ForegroundColor Yellow

# Find containers that use the package cache volume and clear their cache
$containers = docker ps --format "{{.Names}}" | Where-Object { $_ -like "*secure_package_manager*" }

foreach ($container in $containers) {
    Write-Host "Clearing cache in container: $container" -ForegroundColor Cyan
    docker exec $container rm -rf /app/package_cache/* 2>$null
    docker exec $container rm -rf /app/package_cache/.* 2>$null
}

Write-Host "✅ Package cache cleared!" -ForegroundColor Green
Write-Host "💡 The cache will be recreated as packages are downloaded." -ForegroundColor Cyan
