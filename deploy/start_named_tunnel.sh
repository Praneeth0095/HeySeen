#!/bin/bash
# Run the named tunnel using the config and credentials generated

echo "🚀 Starting Named Tunnel..."

# Ensure cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared not found."
    exit 1
fi

# Run
# Note: config.yml assumes relative path to credentials file, need to be careful with CWD.
cd deploy
cloudflared tunnel --config config.yml run heyseen-tunnel
