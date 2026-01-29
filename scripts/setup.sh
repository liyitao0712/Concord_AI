#!/bin/bash

# Concord AI - One-click Setup Script
# Usage: ./scripts/setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Concord AI - One-click Setup"
echo "=========================================="

# 1. Check prerequisites
echo ""
echo "[1/6] Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

echo "  - Docker: OK"
echo "  - Python3: OK"

# 2. Create .env file
echo ""
echo "[2/6] Setting up environment..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  Created .env file from .env.example"
    echo "  Please edit .env to add your API keys!"
else
    echo "  .env file already exists"
fi

# 3. Start Docker containers
echo ""
echo "[3/6] Starting Docker containers..."
docker-compose up -d

# Wait for containers to be healthy
echo "  Waiting for containers to be ready..."
sleep 5

# 4. Create virtual environment
echo ""
echo "[4/6] Creating Python virtual environment..."
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  Virtual environment created"
else
    echo "  Virtual environment already exists"
fi

# 5. Install dependencies
echo ""
echo "[5/6] Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet

# 6. Verify setup
echo ""
echo "[6/6] Verifying setup..."

# Check Docker containers
if docker-compose ps | grep -q "healthy"; then
    echo "  - Docker containers: OK"
else
    echo "  - Docker containers: Starting (may take a moment)"
fi

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env file with your API keys"
echo "  2. Run: ./scripts/start.sh"
echo ""
