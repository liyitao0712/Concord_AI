#!/bin/bash

# Concord AI - Reset Database Script
# Usage: ./scripts/reset-db.sh
# WARNING: This will DELETE ALL DATA!

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Concord AI - Reset Database"
echo "=========================================="
echo ""
echo "WARNING: This will DELETE ALL DATA in the database!"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "[1/3] Stopping containers..."
docker-compose down

echo ""
echo "[2/3] Removing database volume..."
docker volume rm concord_ai_postgres_data 2>/dev/null || true

echo ""
echo "[3/3] Restarting containers..."
docker-compose up -d

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 5

echo ""
echo "=========================================="
echo "  Database Reset Complete!"
echo "=========================================="
echo ""
echo "The database has been reset to a clean state."
echo "Run migrations if needed:"
echo "  cd backend && source venv/bin/activate"
echo "  alembic upgrade head"
echo ""
