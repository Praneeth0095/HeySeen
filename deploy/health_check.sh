#!/bin/bash
# Check status of HeySeen services

echo "===== HeySeen Health Check ====="
echo "Date: $(date)"
echo "--------------------------------"

# Check Uvicorn
if pgrep -f "uvicorn heyseen.server.app:app" > /dev/null; then
    echo "✅ Backend (Uvicorn): RUNNING"
else
    echo "❌ Backend (Uvicorn): STOPPED"
fi

# Check Cloudflared
if pgrep -f "cloudflared tunnel" > /dev/null; then
    echo "✅ Tunnel (Cloudflared): RUNNING"
else
    echo "❌ Tunnel (Cloudflared): STOPPED"
fi

echo "--------------------------------"
echo "Active Ports:"
lsof -i :5555 | grep LISTEN | awk '{print "  Localhost:5555 (PID " $2 ")"}'

echo "--------------------------------"
# Check Logs (last 3 lines)
echo "Recent Server Logs:"
if [ -f server_data/server.log ]; then
    tail -n 3 server_data/server.log | sed 's/^/  /'
else
    echo "  (No log file found)"
fi

echo "Recent Tunnel Logs:"
if [ -f deploy/tunnel.log ]; then
    tail -n 3 deploy/tunnel.log | grep -v "metrics" | sed 's/^/  /'
else
    echo "  (No log file found)"
fi
