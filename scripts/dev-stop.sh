#!/bin/bash
# Development tear-down script
# Usage: ./dev-stop.sh [service_name]
# If no service is specified, stops all services

SERVICE=${1:-""}

if [ -n "$SERVICE" ]; then
    echo "🛑 Stopping development service: $SERVICE..."
else
    echo "🛑 Stopping development environment..."
fi

# Ensure we're using the correct Docker context
echo "🔧 Setting Docker context..."
docker context use default

if [ -n "$SERVICE" ]; then
    # Single service mode - just stop the specified service
    echo "📦 Stopping service: $SERVICE..."
    docker compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml stop "$SERVICE"
    docker compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml rm -f "$SERVICE"
    
    echo "✅ Service '$SERVICE' stopped!"
    echo "💡 To start again, run: ./scripts/dev-start.sh $SERVICE"
else
    # Full environment mode - stop all services
    # Stop and remove all containers
    echo "📦 Stopping containers..."
    docker compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml down

    # Remove volumes (optional - uncomment if you want to completely reset)
    # echo "🗑️  Removing volumes..."
    # docker compose --env-file example.env.development -f docker-compose.base.yml -f docker-compose.dev.yml down -v

    # Remove any dangling images (optional)
    # echo "🧹 Cleaning up dangling images..."
    # docker image prune -f

    echo "✅ Development environment stopped!"
    echo "💡 To start again, run: ./scripts/dev-start.sh"
    echo "💡 To completely reset (including database), run: ./scripts/dev-reset.sh"
fi
