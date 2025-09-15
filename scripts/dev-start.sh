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
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

echo "✅ Development environment started!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 API: http://localhost:5000"
echo "🗄️  Database: localhost:5432"
echo "🔍 Trivy: http://localhost:4954"
echo "🔐 Mock IDP: http://localhost:8081"
echo "📦 Mock NPM Registry: http://localhost:8080"
