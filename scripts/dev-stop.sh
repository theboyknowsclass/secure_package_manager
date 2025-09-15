#!/bin/bash
# Development tear-down script

echo "🛑 Stopping development environment..."

# Stop and remove all containers
echo "📦 Stopping containers..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Remove volumes (optional - uncomment if you want to completely reset)
# echo "🗑️  Removing volumes..."
# docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v

# Remove any dangling images (optional)
# echo "🧹 Cleaning up dangling images..."
# docker image prune -f

echo "✅ Development environment stopped!"
echo "💡 To start again, run: ./scripts/dev-start.sh"
echo "💡 To completely reset (including database), run: ./scripts/dev-reset.sh"
