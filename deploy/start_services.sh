#!/bin/bash

# Ensure we are in project root
cd "$(dirname "$0")/.."

echo "🚀 Starting HeySeen Service (API + Frontend)..."

# Create data directories
mkdir -p server_data/uploads
mkdir -p server_data/outputs

# Start Backend (FastAPI serving both API and Static)
echo "Starting Server on port 5555..."
source .venv/bin/activate
nohup uvicorn heyseen.server.app:app --host 0.0.0.0 --port 5555 > server_data/server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > server_data/server.pid
echo "✓ Server running (PID: $SERVER_PID)"
echo "  -> http://localhost:5555"

echo ""
echo "To stop services: ./deploy/stop_services.sh"
