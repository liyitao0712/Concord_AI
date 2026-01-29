#!/bin/bash

# Concord AI - Status Script
# Usage: ./scripts/status.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Concord AI - Service Status"
echo "=========================================="

echo ""
echo "Docker Containers:"
echo "------------------------------------------"
docker-compose ps

echo ""
echo "Port Usage:"
echo "------------------------------------------"
echo "  PostgreSQL: 5432"
echo "  Redis:      6379"
echo "  FastAPI:    8000"

echo ""
echo "Health Check:"
echo "------------------------------------------"

# Check FastAPI
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "  FastAPI:    Running"
else
    echo "  FastAPI:    Not running"
fi

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "  PostgreSQL: Running"
else
    echo "  PostgreSQL: Not running"
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "  Redis:      Running"
else
    echo "  Redis:      Not running"
fi

echo ""
