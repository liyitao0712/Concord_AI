#!/bin/bash

# Concord AI - Database Migration Script
# Usage:
#   ./scripts/migrate.sh                    # Run migrations
#   ./scripts/migrate.sh create "message"   # Create new migration
#   ./scripts/migrate.sh downgrade          # Rollback last migration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/backend"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found. Run ./scripts/setup.sh first."
    exit 1
fi

ACTION=${1:-upgrade}
MESSAGE=$2

case $ACTION in
    upgrade|up)
        echo "Running migrations..."
        alembic upgrade head
        echo "Migrations complete."
        ;;
    downgrade|down)
        echo "Rolling back last migration..."
        alembic downgrade -1
        echo "Rollback complete."
        ;;
    create|new)
        if [ -z "$MESSAGE" ]; then
            echo "Error: Please provide a migration message"
            echo "Usage: ./scripts/migrate.sh create \"your message\""
            exit 1
        fi
        echo "Creating new migration: $MESSAGE"
        alembic revision --autogenerate -m "$MESSAGE"
        echo "Migration created. Check alembic/versions/"
        ;;
    history)
        echo "Migration history:"
        alembic history
        ;;
    current)
        echo "Current migration:"
        alembic current
        ;;
    *)
        echo "Usage: ./scripts/migrate.sh [command]"
        echo ""
        echo "Commands:"
        echo "  upgrade, up     Run all pending migrations (default)"
        echo "  downgrade, down Rollback last migration"
        echo "  create, new     Create new migration (requires message)"
        echo "  history         Show migration history"
        echo "  current         Show current migration"
        ;;
esac
