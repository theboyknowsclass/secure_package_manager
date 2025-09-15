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

# Stop any existing containers
echo "📦 Stopping existing containers..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Start services with production configuration
echo "🔄 Starting production services..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo "✅ Production environment started!"
echo "🔧 Services are running in detached mode"
echo "📊 Use 'docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f' to view logs"
