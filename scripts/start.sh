#!/bin/bash

# Concord AI - Start Script
# Usage: ./scripts/start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Starting Concord AI"
echo "=========================================="

# 1. Start Docker containers
echo ""
echo "[1/3] Starting Docker containers..."
docker-compose up -d

# Wait for containers to be healthy
echo "Waiting for containers to be healthy..."
sleep 3

# Check container status
if ! docker-compose ps | grep -q "healthy"; then
    echo "Warning: Some containers may not be healthy yet"
    docker-compose ps
fi

# 2. Activate virtual environment
echo ""
echo "[2/3] Activating virtual environment..."
cd backend

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Run ./scripts/setup.sh first."
    exit 1
fi

source venv/bin/activate

# 3. Start FastAPI server
echo ""
echo "[3/3] Starting FastAPI server..."
echo ""
echo "=========================================="
echo "  Server starting at http://localhost:8000"
echo "  API docs at http://localhost:8000/docs"
echo "  Press Ctrl+C to stop"
echo "=========================================="
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
