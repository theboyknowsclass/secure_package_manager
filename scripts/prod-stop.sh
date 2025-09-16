#!/bin/bash
# Production tear-down script

echo "🛑 Stopping production environment..."

# Ensure we're using the correct Docker context
echo "🔧 Setting Docker context..."
docker context use default

# Stop and remove all containers
echo "📦 Stopping containers..."
docker compose --env-file .env.production -f docker-compose.base.yml -f docker-compose.prod.yml down

echo "✅ Production environment stopped!"
echo "💡 To start again, run: ./scripts/prod-start.sh"
echo "💡 To completely reset (including database), run: ./scripts/prod-reset.sh"
echo "⚠️  Note: Database data is preserved. Use 'docker-compose down -v' to remove volumes."
