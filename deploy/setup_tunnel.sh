#!/bin/bash

# Configuration
DOMAIN="heyseen.truyenthong.edu.vn"
TUNNEL_NAME="heyseen-tunnel"

echo "🚀 Setting up Cloudflare Tunnel for $DOMAIN..."

# Check cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared not found. Installing via Homebrew..."
    brew install cloudflared
fi

# Login
echo "Please login to Cloudflare (select truyenthong.edu.vn zone):"
cloudflared tunnel login

# Create Tunnel
echo "Creating tunnel '$TUNNEL_NAME'..."
cloudflared tunnel create $TUNNEL_NAME

# Get Tunnel ID (grep from list or json)
TUNNEL_ID=$(cloudflared tunnel list | grep $TUNNEL_NAME | awk '{print $1}')
echo "✅ Tunnel Configured. ID: $TUNNEL_ID"

# Generate Config
echo "Generating config.yml..."
cat > deploy/config.yml << EOL
tunnel: $TUNNEL_ID
credentials-file: /Users/$USER/.cloudflared/$TUNNEL_ID.json

ingress:
  # API Endpoints mapped to Backend (5555)
  - hostname: $DOMAIN
    path: /convert
    service: http://localhost:5555
  - hostname: $DOMAIN
    path: /status/*
    service: http://localhost:5555
  - hostname: $DOMAIN
    path: /download/*
    service: http://localhost:5555
  - hostname: $DOMAIN
    path: /docs
    service: http://localhost:5555
  - hostname: $DOMAIN
    path: /openapi.json
    service: http://localhost:5555

  # Frontend mapped to Static Server (5556)
  - hostname: $DOMAIN
    service: http://localhost:5556
  
  # Catch-all
  - service: http_status:404
EOL

# Route DNS
echo "Routing DNS..."
cloudflared tunnel route dns $TUNNEL_NAME $DOMAIN

echo "✅ Setup Complete!"
echo "To start the tunnel run:"
echo "cloudflared tunnel run $TUNNEL_NAME"
