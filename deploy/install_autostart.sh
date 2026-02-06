#!/bin/bash

# Absolute path to project root
PROJECT_ROOT="/Users/m2pro/HeySeen"
USER_ID=$(id -u)
GROUP_ID=$(id -g)

echo "🚀 Setting up Auto-start for HeySeen..."

# 1. Create Server Plist
SERVER_PLIST="$HOME/Library/LaunchAgents/vn.edu.truyenthong.heyseen.server.plist"
echo "Creating $SERVER_PLIST..."

cat > "$SERVER_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>vn.edu.truyenthong.heyseen.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_ROOT/.venv/bin/uvicorn</string>
        <string>heyseen.server.app:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>5555</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_ROOT</string>
    <key>StandardOutPath</key>
    <string>$PROJECT_ROOT/server_data/server.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_ROOT/server_data/server.log</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

# 2. Create Tunnel Plist
TUNNEL_PLIST="$HOME/Library/LaunchAgents/vn.edu.truyenthong.heyseen.tunnel.plist"
echo "Creating $TUNNEL_PLIST..."

# Find cloudflared path
CLOUDFLARED_PATH=$(which cloudflared)
if [ -z "$CLOUDFLARED_PATH" ]; then
    CLOUDFLARED_PATH="/opt/homebrew/bin/cloudflared" # Fallback
fi

cat > "$TUNNEL_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>vn.edu.truyenthong.heyseen.tunnel</string>
    <key>ProgramArguments</key>
    <array>
        <string>$CLOUDFLARED_PATH</string>
        <string>tunnel</string>
        <string>--config</string>
        <string>config.yml</string>
        <string>run</string>
        <string>heyseen-tunnel</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_ROOT/deploy</string>
    <key>StandardOutPath</key>
    <string>$PROJECT_ROOT/deploy/tunnel.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_ROOT/deploy/tunnel.log</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

# 3. Stop running processes first
echo "Stopping existing services..."
$PROJECT_ROOT/deploy/stop_services.sh
pkill cloudflared

# 4. Load Plists
echo "Loading LaunchAgents..."
launchctl bootout gui/$USER_ID "$SERVER_PLIST" 2>/dev/null
launchctl bootout gui/$USER_ID "$TUNNEL_PLIST" 2>/dev/null

launchctl bootstrap gui/$USER_ID "$SERVER_PLIST"
launchctl bootstrap gui/$USER_ID "$TUNNEL_PLIST"

echo "✅ Auto-start installed and services started!"
echo "   Server Status: launchctl list | grep heyseen.server"
echo "   Tunnel Status: launchctl list | grep heyseen.tunnel"
