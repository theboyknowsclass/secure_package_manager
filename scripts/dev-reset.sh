#!/bin/bash
# Development complete reset script - removes everything including database

echo "🔄 Completely resetting development environment..."

# Ensure we're using the correct Docker context
echo "🔧 Setting Docker context..."
docker context use default

# Stop and remove all containers and volumes
echo "📦 Stopping containers and removing volumes..."
docker-compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml down -v

# Remove any dangling images and build cache
echo "🧹 Cleaning up Docker resources..."
docker image prune -f
docker builder prune -f

# Remove specific volumes if they exist
echo "🗑️  Removing specific volumes..."
docker volume rm secure_package_manager_postgres_data 2>/dev/null || true
docker volume rm secure_package_manager_npm_storage 2>/dev/null || true
docker volume rm secure_package_manager_package_cache 2>/dev/null || true
docker volume rm secure_package_manager_trivy_cache 2>/dev/null || true

echo "✅ Development environment completely reset!"
echo "💡 To start fresh, run: ./scripts/dev-start.sh"
