#!/bin/bash
# Development startup script - fresh database every time
# Usage: ./dev-start.sh [service_name]
# If no service is specified, starts all services

# set the IP address for a env var called "localhost" so we can dynamically set the ip for various env vars
# if no IP found, set the env var "localhost" to "localhost"
ip_address=$(hostname -I | awk '{print $1}')

if [ -z "${ip_address}" ]; then
   ip_address="localhost"
fi
export localhost=${ip_address}

SERVICE=${1:-""}

if [ -n "$SERVICE" ]; then
    echo "🚀 Starting development service: $SERVICE..."
else
    echo "🚀 Starting development environment with fresh database..."
fi

# Ensure we're using the correct Docker context
echo "🔧 Setting Docker context..."
docker context use default

if [ -n "$SERVICE" ]; then
    # Single service mode - just start the specified service
    echo "🔄 Starting service: $SERVICE..."
    docker-compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml up --build -d "$SERVICE"
else
    # Full environment mode - fresh start with clean database
    # Stop and remove all containers
    echo "📦 Stopping existing containers..."
    docker-compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml down -v

    # Remove any existing database volumes to ensure fresh start
    echo "🗑️  Removing database volumes..."
    docker volume rm secure_package_manager_postgres_data 2>/dev/null || true
    docker volume rm secure_package_manager_npm_storage 2>/dev/null || true

    # Start services with dev configuration
    echo "🔄 Starting services..."
    docker-compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml up --build -d
fi

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."

if [ -n "$SERVICE" ]; then
    # Check single service status
    service_status=$(docker-compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml ps "$SERVICE" --format "table {{.Service}}\t{{.Status}}")
    if echo "$service_status" | grep -q "Up"; then
        echo "✅ Service '$SERVICE' started successfully!"
        echo "📋 Service status:"
        echo "$service_status"
    else
        echo "❌ Service '$SERVICE' failed to start. Check logs with:"
        echo "   docker-compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml logs $SERVICE"
        exit 1
    fi
else
    # Check all services status
    services=$(docker-compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml ps --services | wc -l)
    running=$(docker-compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml ps --services --filter "status=running" | wc -l)

    if [ "$services" -eq "$running" ]; then
        echo "✅ Development environment started successfully!"
        echo "🌐 Frontend: http://${localhost}:3000"
        echo "🔧 API: http://${localhost}:5000"
        echo "🗄️  Database: ${localhost}:5432"
        echo "🔍 Trivy: http://${localhost}:4954"
        echo "🔐 Mock IDP: http://${localhost}:8081"
        echo "📦 Mock NPM Registry: http://${localhost}:8080"
        echo "📦 PGAdmin4: http://${localhost}:5050"
    else
        echo "❌ Some services failed to start. Check logs with:"
        echo "   docker-compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml logs"
        exit 1
    fi
fi
