#!/bin/bash

# Concord AI - View Logs Script
# Usage: ./scripts/logs.sh [service]
# Examples:
#   ./scripts/logs.sh          # All services
#   ./scripts/logs.sh postgres # PostgreSQL only
#   ./scripts/logs.sh redis    # Redis only

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

SERVICE=$1

if [ -z "$SERVICE" ]; then
    echo "Showing logs for all services (Ctrl+C to exit)..."
    docker-compose logs -f
else
    echo "Showing logs for $SERVICE (Ctrl+C to exit)..."
    docker-compose logs -f "$SERVICE"
fi
