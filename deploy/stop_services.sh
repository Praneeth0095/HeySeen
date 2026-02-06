#!/bin/bash

# Ensure we are in project root
cd "$(dirname "$0")/.."

echo "🛑 Stopping HeySeen Services..."

if [ -f server_data/server.pid ]; then
    PID=$(cat server_data/server.pid)
    kill $PID 2>/dev/null
    rm server_data/server.pid
    echo "✓ Stopped Backend ($PID)"
else
    # Fallback to pattern matching
    echo "  (PID file not found, trying pkill...)"
    pkill -f "uvicorn heyseen.server.app:app"
fi

# Frontend is now part of backend
# if [ -f server_data/frontend.pid ]; then ... fi

echo "Done."
