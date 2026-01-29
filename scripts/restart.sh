#!/bin/bash

# Concord AI - Restart Script
# Usage: ./scripts/restart.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Restarting Concord AI"
echo "=========================================="

# Stop services
echo ""
echo "[1/2] Stopping services..."
docker-compose down

# Start services
echo ""
echo "[2/2] Starting services..."
docker-compose up -d

# Wait for containers
sleep 3

echo ""
echo "Docker containers restarted."
docker-compose ps

echo ""
echo "To start the FastAPI server, run:"
echo "  cd backend && source venv/bin/activate"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
