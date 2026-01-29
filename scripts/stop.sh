#!/bin/bash

# Concord AI - Stop Script
# Usage: ./scripts/stop.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Stopping Concord AI"
echo "=========================================="

# Stop Docker containers
echo ""
echo "Stopping Docker containers..."
docker-compose down

echo ""
echo "All services stopped."
