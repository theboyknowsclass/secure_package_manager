#!/bin/bash
# Development startup script - fresh database every time

echo "🚀 Starting development environment with fresh database..."

# Stop and remove all containers
echo "📦 Stopping existing containers..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v

# Remove any existing database volumes to ensure fresh start
echo "🗑️  Removing database volumes..."
docker volume rm secure_package_manager_postgres_data 2>/dev/null || true
docker volume rm secure_package_manager_npm_storage 2>/dev/null || true

# Start services with dev configuration
echo "🔄 Starting services..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."
services=$(docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps --services | wc -l)
running=$(docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps --services --filter "status=running" | wc -l)

if [ "$services" -eq "$running" ]; then
    echo "✅ Development environment started successfully!"
    echo "🌐 Frontend: http://localhost:3000"
    echo "🔧 API: http://localhost:5000"
    echo "🗄️  Database: localhost:5432"
    echo "🔍 Trivy: http://localhost:4954"
    echo "🔐 Mock IDP: http://localhost:8081"
    echo "📦 Mock NPM Registry: http://localhost:8080"
else
    echo "❌ Some services failed to start. Check logs with:"
    echo "   docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs"
    exit 1
fi
