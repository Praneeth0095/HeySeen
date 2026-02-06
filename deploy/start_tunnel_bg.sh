#!/bin/bash
cd "$(dirname "$0")/.."

echo "🚀 Starting Named Tunnel in Background..."

# Check if already running
if pgrep -f "cloudflared tunnel --config config.yml run" > /dev/null; then
  echo "⚠️  Tunnel is already running."
  exit 0
fi

cd deploy
nohup cloudflared tunnel --config config.yml run heyseen-tunnel > tunnel.log 2>&1 &
TUNNEL_PID=$!
echo "✓ Tunnel started (PID: $TUNNEL_PID)"
echo "  -> Check deploy/tunnel.log for details"
