#!/bin/bash
# MeetingBox Device UI Installation Script
# Tested on Raspberry Pi OS Bookworm (Debian 12)

set -e  # Exit on error

echo "=========================================="
echo "MeetingBox Device UI Installation"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Get the actual user who called sudo
ACTUAL_USER=${SUDO_USER:-$USER}
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

# Installation paths
INSTALL_DIR="/opt/meetingbox/device-ui"
VENV_DIR="$INSTALL_DIR/venv"
SYSTEMD_DIR="/etc/systemd/system"

echo ""
echo "1. Installing system dependencies..."
apt-get update
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-full \
    python3-dev \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libgl1-mesa-dev \
    libgstreamer1.0-dev \
    libmtdev1 \
    xserver-xorg \
    xinit \
    unclutter

echo ""
echo "2. Creating installation directory..."
mkdir -p $INSTALL_DIR
chown -R $ACTUAL_USER:$ACTUAL_USER /opt/meetingbox

echo ""
echo "3. Copying device-ui files..."
cp -r device-ui/* $INSTALL_DIR/
chown -R $ACTUAL_USER:$ACTUAL_USER $INSTALL_DIR

echo ""
echo "4. Creating Python virtual environment..."
sudo -u $ACTUAL_USER python3 -m venv $VENV_DIR
echo "   Virtual environment created at $VENV_DIR"

echo ""
echo "5. Installing Python dependencies in venv..."
sudo -u $ACTUAL_USER $VENV_DIR/bin/pip install --upgrade pip
sudo -u $ACTUAL_USER $VENV_DIR/bin/pip install -r $INSTALL_DIR/requirements.txt
echo "   Dependencies installed successfully"

echo ""
echo "6. Setting up systemd service..."

cat > $SYSTEMD_DIR/meetingbox-ui.service << EOF
[Unit]
Description=MeetingBox OLED Display UI
After=network.target meetingbox-backend.service
Requires=meetingbox-backend.service

[Service]
Type=simple
User=$ACTUAL_USER
Environment="DISPLAY=:0"
Environment="BACKEND_URL=http://localhost:8000"
Environment="KIVY_NO_CONSOLELOG=1"
WorkingDirectory=$INSTALL_DIR
ExecStartPre=/bin/sleep 5
ExecStart=$VENV_DIR/bin/python $INSTALL_DIR/src/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=meetingbox-ui

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "7. Setting up backend service (Docker Compose)..."

cat > $SYSTEMD_DIR/meetingbox-backend.service << EOF
[Unit]
Description=MeetingBox Backend Services (Docker Compose)
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=$ACTUAL_USER
WorkingDirectory=/opt/meetingbox
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "8. Enabling and starting services..."
systemctl daemon-reload
systemctl enable meetingbox-backend.service
systemctl enable meetingbox-ui.service

echo ""
echo "9. Starting backend services..."
systemctl start meetingbox-backend.service
echo "   Waiting for backend to be ready..."
sleep 10

echo ""
echo "10. Starting device UI..."
systemctl start meetingbox-ui.service
sleep 3
systemctl status meetingbox-ui.service --no-pager || true

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "Python venv:      $VENV_DIR"
echo "Python binary:    $VENV_DIR/bin/python"
echo ""
echo "Service commands:"
echo "  Status:   systemctl status meetingbox-ui"
echo "  Logs:     journalctl -u meetingbox-ui -f"
echo "  Restart:  systemctl restart meetingbox-ui"
echo "  Backend:  systemctl status meetingbox-backend"
echo ""
echo "To run the UI manually (for debugging):"
echo "  cd $INSTALL_DIR"
echo "  DISPLAY=:0 MOCK_BACKEND=1 $VENV_DIR/bin/python src/main.py"
echo ""
