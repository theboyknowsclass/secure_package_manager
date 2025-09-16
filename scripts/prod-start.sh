#!/bin/bash
# Production startup script

echo "🚀 Starting production environment..."

# Check for required environment variables
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "❌ Error: POSTGRES_PASSWORD environment variable is required"
    exit 1
fi

if [ -z "$ADFS_ENTITY_ID" ] || [ -z "$ADFS_SSO_URL" ]; then
    echo "❌ Error: ADFS_ENTITY_ID and ADFS_SSO_URL environment variables are required"
    exit 1
fi

# Ensure we're using the correct Docker context
echo "🔧 Setting Docker context..."
docker context use default

# Stop any existing containers
echo "📦 Stopping existing containers..."
docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml down

# Start services with production configuration
echo "🔄 Starting production services..."
docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml up -d --build

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 15

# Check if services are running
echo "🔍 Checking service status..."
services=$(docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml ps --services | wc -l)
running=$(docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml ps --services --filter "status=running" | wc -l)

if [ "$services" -eq "$running" ]; then
    echo "✅ Production environment started successfully!"
    echo "🔧 Services are running in detached mode"
    echo "📊 Use 'docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml logs -f' to view logs"
else
    echo "❌ Some services failed to start. Check logs with:"
    echo "   docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml logs"
    exit 1
fi
