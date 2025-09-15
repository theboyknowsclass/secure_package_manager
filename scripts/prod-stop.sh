#!/bin/bash
# Production tear-down script

echo "🛑 Stopping production environment..."

# Stop and remove all containers
echo "📦 Stopping containers..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

echo "✅ Production environment stopped!"
echo "💡 To start again, run: ./scripts/prod-start.sh"
echo "⚠️  Note: Database data is preserved. Use 'docker-compose down -v' to remove volumes."
