#!/bin/bash
# Production complete reset script - removes everything including database - USE WITH CAUTION!

echo "⚠️  WARNING: This will completely reset the production environment!"
echo "⚠️  All data including the database will be permanently deleted!"
echo ""

# Confirmation prompt
read -p "Are you sure you want to continue? Type 'RESET' to confirm: " confirmation
if [ "$confirmation" != "RESET" ]; then
    echo "❌ Operation cancelled."
    exit 0
fi

echo "🔄 Completely resetting production environment..."

# Check for required environment variables
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "❌ Error: POSTGRES_PASSWORD environment variable is required"
    exit 1
fi

if [ -z "$ADFS_ENTITY_ID" ] || [ -z "$ADFS_SSO_URL" ]; then
    echo "❌ Error: ADFS_ENTITY_ID and ADFS_SSO_URL environment variables are required"
    exit 1
fi

# Stop and remove all containers and volumes
echo "📦 Stopping containers and removing volumes..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down -v

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

echo "✅ Production environment completely reset!"
echo "💡 To start fresh, run: ./scripts/prod-start.sh"
echo "⚠️  Remember: You'll need to restore any production data from backups!"
