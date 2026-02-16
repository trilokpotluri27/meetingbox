#!/bin/bash
# ============================================================
# MeetingBox Installation Script
# ============================================================
# Installs everything via Docker. The device-ui, backend,
# transcription, audio, and AI services all run as containers.
#
# The ONLY host-level setup needed is:
#   1. Docker + Docker Compose
#   2. X11 display server (for the touchscreen)
#   3. xhost permission so the container can draw on the screen
#
# Tested on Raspberry Pi OS Bookworm (Debian 12)
# ============================================================

set -e

echo "=========================================="
echo "  MeetingBox Full Installation"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Get the actual user who called sudo
ACTUAL_USER=${SUDO_USER:-$USER}
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)
INSTALL_DIR="/opt/meetingbox"

# -------------------------------------------------------
# 1. System dependencies (minimal — just X11 & display)
# -------------------------------------------------------
echo ""
echo "1/7  Installing system dependencies..."
apt-get update
apt-get install -y --no-install-recommends \
    xserver-xorg \
    xinit \
    x11-xserver-utils \
    unclutter \
    xdotool \
    docker.io \
    docker-compose-plugin \
    git

# Ensure user is in required groups
usermod -aG docker,video,input,audio "$ACTUAL_USER"

# -------------------------------------------------------
# 2. Copy project files
# -------------------------------------------------------
echo ""
echo "2/7  Setting up project directory..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/data/config"
mkdir -p "$INSTALL_DIR/data/audio/recordings"
mkdir -p "$INSTALL_DIR/data/transcripts"

# If we're in the repo, copy everything over
if [ -f "docker-compose.yml" ]; then
    echo "   Copying project files to $INSTALL_DIR..."
    rsync -a --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
        . "$INSTALL_DIR/"
fi
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$INSTALL_DIR"

# -------------------------------------------------------
# 3. Configure X11 display
# -------------------------------------------------------
echo ""
echo "3/7  Configuring display..."

# Auto-start X on tty1 login
BASHRC="$ACTUAL_HOME/.bashrc"
if ! grep -q "startx" "$BASHRC" 2>/dev/null; then
    cat >> "$BASHRC" << 'XSTART'

# Auto-start X on tty1 (MeetingBox display)
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    startx -- -nocursor 2>/dev/null
fi
XSTART
fi

# Create .xinitrc — starts X, disables blanking, allows Docker to draw
cat > "$ACTUAL_HOME/.xinitrc" << 'XINIT'
#!/bin/sh
# Disable screen blanking & power management
xset s off
xset -dpms
xset s noblank

# Allow any local process (including Docker) to use the display
xhost +local:

# Hide cursor after 0.5s idle
unclutter -idle 0.5 -root &

# Keep X running (systemd services draw on this display)
while true; do sleep 3600; done
XINIT

chmod +x "$ACTUAL_HOME/.xinitrc"
chown "$ACTUAL_USER:$ACTUAL_USER" "$ACTUAL_HOME/.xinitrc" "$BASHRC"

# -------------------------------------------------------
# 4. Auto-login on tty1 (so X starts on boot)
# -------------------------------------------------------
echo ""
echo "4/7  Configuring auto-login on tty1..."

AUTOLOGIN_DIR="/etc/systemd/system/getty@tty1.service.d"
mkdir -p "$AUTOLOGIN_DIR"
cat > "$AUTOLOGIN_DIR/override.conf" << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $ACTUAL_USER --noclear %I \$TERM
EOF

# -------------------------------------------------------
# 5. Systemd service for Docker Compose
# -------------------------------------------------------
echo ""
echo "5/7  Creating systemd service..."

cat > /etc/systemd/system/meetingbox.service << EOF
[Unit]
Description=MeetingBox (all services via Docker Compose)
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=$ACTUAL_USER
WorkingDirectory=$INSTALL_DIR
ExecStartPre=/bin/bash -c 'until docker info >/dev/null 2>&1; do sleep 2; done'
ExecStart=/usr/bin/docker compose up -d --build
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable meetingbox.service

# -------------------------------------------------------
# 6. Build & start all containers
# -------------------------------------------------------
echo ""
echo "6/7  Building and starting Docker containers..."
cd "$INSTALL_DIR"
sudo -u "$ACTUAL_USER" docker compose build
sudo -u "$ACTUAL_USER" docker compose up -d

echo "   Waiting for services to start..."
sleep 10

# Quick health check
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "   ✓ Backend is healthy"
else
    echo "   ⚠ Backend not responding yet (may still be starting)"
fi

# Check UI container
if docker ps --format '{{.Names}}' | grep -q meetingbox-ui; then
    echo "   ✓ Device UI container is running"
else
    echo "   ⚠ Device UI container not running — check: docker logs meetingbox-ui"
fi

# -------------------------------------------------------
# 7. Done
# -------------------------------------------------------
echo ""
echo "7/7  Enabling mDNS (meetingbox.local)..."
apt-get install -y --no-install-recommends avahi-daemon avahi-utils 2>/dev/null || true
systemctl enable avahi-daemon 2>/dev/null || true
systemctl start avahi-daemon 2>/dev/null || true

echo ""
echo "=========================================="
echo "  Installation complete!"
echo "=========================================="
echo ""
echo "All services run inside Docker. Nothing is installed"
echo "on the host Python — no venv needed."
echo ""
echo "  Project dir:     $INSTALL_DIR"
echo "  Web dashboard:   http://meetingbox.local:8000"
echo "  API health:      http://localhost:8000/health"
echo ""
echo "Commands:"
echo "  docker compose ps              # See running containers"
echo "  docker compose logs -f         # Follow all logs"
echo "  docker logs meetingbox-ui -f   # Device UI logs only"
echo "  docker compose restart         # Restart everything"
echo "  docker compose down            # Stop everything"
echo "  docker compose up -d --build   # Rebuild & restart"
echo ""
echo "The screen UI will appear after reboot (X11 auto-starts)."
echo "Reboot now?  sudo reboot"
echo ""
