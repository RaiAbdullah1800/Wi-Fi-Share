#!/usr/bin/env bash

# Setup Auto-Start script for Wi-Fi File Sharing Application
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/wifi-share.desktop"

echo "======================================================"
echo "⚙️  Configuring Auto-Start for Wi-Fi File Sharing App"
echo "======================================================"
echo "App Directory: $APP_DIR"

mkdir -p "$AUTOSTART_DIR"

cat << 'EOF' > "$DESKTOP_FILE"
[Desktop Entry]
Type=Application
Name=Wi-Fi File Sharing App
Comment=Automatically starts the Wi-Fi File and Text Sharing Server
Exec=python3 APP_DIR_PLACEHOLDER/app.py
Path=APP_DIR_PLACEHOLDER
Terminal=false
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF

sed -i "s|APP_DIR_PLACEHOLDER|$APP_DIR|g" "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"

echo "✅ Created autostart launcher at: $DESKTOP_FILE"
echo "🚀 The application will now launch automatically whenever you log in!"
echo "======================================================"
