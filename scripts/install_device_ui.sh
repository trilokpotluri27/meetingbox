#!/bin/bash
# MeetingBox Full Installation Script
# Sets up the Raspberry Pi display, then runs everything via Docker Compose.
# Tested on Raspberry Pi OS Bookworm (Debian 12)

set -e

echo "=========================================="
echo "MeetingBox Installation"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

ACTUAL_USER=${SUDO_USER:-$USER}
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)
PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)

# ─── 1. System dependencies (display + Docker) ──────────────────

echo ""
echo "1. Installing system dependencies..."
apt-get update
apt-get install -y \
    xserver-xorg \
    xinit \
    x11-xserver-utils \
    unclutter \
    docker.io \
    docker-compose-plugin

# Add user to required groups
usermod -aG docker,video,input,audio "$ACTUAL_USER" 2>/dev/null || true

# ─── 2. Configure X11 display ───────────────────────────────────

echo ""
echo "2. Configuring X11 display..."

DISPLAY_WIDTH=${DISPLAY_WIDTH:-480}
DISPLAY_HEIGHT=${DISPLAY_HEIGHT:-320}

mkdir -p /etc/X11/xorg.conf.d
cat > /etc/X11/xorg.conf.d/99-meetingbox-display.conf << EOF
Section "Monitor"
    Identifier "MeetingBox-Display"
    Option "PreferredMode" "${DISPLAY_WIDTH}x${DISPLAY_HEIGHT}"
EndSection

Section "Screen"
    Identifier "Default Screen"
    Monitor "MeetingBox-Display"
    DefaultDepth 24
EndSection
EOF

# ─── 3. Auto-start X on boot (tty1) ─────────────────────────────

echo ""
echo "3. Setting up auto-start X on boot..."

BASHRC="$ACTUAL_HOME/.bashrc"
AUTOSTART_LINE='if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then startx -- -nocursor; fi'

if ! grep -qF 'startx' "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# Auto-start X for MeetingBox display" >> "$BASHRC"
    echo "$AUTOSTART_LINE" >> "$BASHRC"
fi

# ─── 4. Create .xinitrc ─────────────────────────────────────────

echo ""
echo "4. Creating .xinitrc..."

cat > "$ACTUAL_HOME/.xinitrc" << 'XINITRC'
#!/bin/sh
# Disable screen blanking and power management
xset s off
xset -dpms
xset s noblank

# Hide cursor after 0.1s of inactivity
unclutter -idle 0.1 &

# Allow Docker containers to connect to X11
xhost +local:docker

# Keep X running (Docker container renders to this display)
while true; do
    sleep 60
done
XINITRC

chmod +x "$ACTUAL_HOME/.xinitrc"
chown "$ACTUAL_USER:$ACTUAL_USER" "$ACTUAL_HOME/.xinitrc"

# ─── 5. Allow X11 access for Docker ─────────────────────────────

echo ""
echo "5. Configuring X11 access for Docker..."

# Create a systemd service to grant docker X11 access on boot
cat > /etc/systemd/system/meetingbox-xhost.service << EOF
[Unit]
Description=Grant Docker X11 access for MeetingBox
After=display-manager.service

[Service]
Type=oneshot
Environment="DISPLAY=:0"
ExecStart=/usr/bin/xhost +local:docker
User=$ACTUAL_USER

[Install]
WantedBy=graphical.target
EOF

systemctl daemon-reload
systemctl enable meetingbox-xhost.service 2>/dev/null || true

# ─── 6. Create data directories ─────────────────────────────────

echo ""
echo "6. Creating data directories..."

mkdir -p "$PROJECT_DIR/data/audio/recordings"
mkdir -p "$PROJECT_DIR/data/transcripts"
mkdir -p "$PROJECT_DIR/data/config"
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$PROJECT_DIR/data"

# ─── 7. Enable Docker on boot ───────────────────────────────────

echo ""
echo "7. Enabling Docker on boot..."
systemctl enable docker

# ─── 8. Build and start Docker Compose ───────────────────────────

echo ""
echo "8. Building Docker containers (this may take a while)..."
cd "$PROJECT_DIR"
sudo -u "$ACTUAL_USER" docker compose build

echo ""
echo "9. Starting all services..."
sudo -u "$ACTUAL_USER" docker compose up -d

echo ""
echo "10. Checking service status..."
sleep 5
sudo -u "$ACTUAL_USER" docker compose ps

# ─── 11. Auto-start Docker Compose on boot ──────────────────────

echo ""
echo "11. Setting up auto-start on boot..."

cat > /etc/systemd/system/meetingbox.service << EOF
[Unit]
Description=MeetingBox (Docker Compose)
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=$ACTUAL_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=180

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable meetingbox.service

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "All services are running in Docker."
echo "The display UI will render to your screen."
echo ""
echo "Commands:"
echo "  docker compose ps              # Check all services"
echo "  docker compose logs -f device-ui  # Device UI logs"
echo "  docker compose logs -f web     # Backend logs"
echo "  docker compose restart device-ui  # Restart UI"
echo "  docker compose down            # Stop everything"
echo "  docker compose up -d           # Start everything"
echo ""
echo "To test without a screen (mock mode):"
echo "  MOCK_BACKEND=1 docker compose up device-ui"
echo ""
echo "Reboot to verify auto-start: sudo reboot"
echo ""
