#!/bin/bash
# Complete cleanup script - removes all project-related Docker resources

echo "🧹 Complete Docker cleanup for Secure Package Manager..."

# Stop all containers
echo "📦 Stopping all containers..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v 2>/dev/null || true
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down -v 2>/dev/null || true

# Remove all project-related volumes
echo "🗑️  Removing all volumes..."
docker volume rm secure_package_manager_postgres_data 2>/dev/null || true
docker volume rm secure_package_manager_npm_storage 2>/dev/null || true
docker volume rm secure_package_manager_package_cache 2>/dev/null || true
docker volume rm secure_package_manager_trivy_cache 2>/dev/null || true

# Remove project images
echo "🖼️  Removing project images..."
docker images | grep secure_package_manager | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true

# Clean up Docker system
echo "🧹 Cleaning up Docker system..."
docker system prune -f
docker builder prune -f

echo "✅ Complete cleanup finished!"
echo "💡 All Secure Package Manager Docker resources have been removed."
echo "💡 To start fresh, run: ./scripts/dev-start.sh"
