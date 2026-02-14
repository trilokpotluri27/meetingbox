#!/bin/bash
# MeetingBox Device UI Installation Script

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
SYSTEMD_DIR="/etc/systemd/system"

echo ""
echo "1. Installing system dependencies..."
apt-get update
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libgl1-mesa-dev \
    xserver-xorg \
    xinit

echo ""
echo "2. Creating installation directory..."
mkdir -p $INSTALL_DIR
chown -R $ACTUAL_USER:$ACTUAL_USER /opt/meetingbox

echo ""
echo "3. Copying device-ui files..."
cp -r device-ui/* $INSTALL_DIR/
chown -R $ACTUAL_USER:$ACTUAL_USER $INSTALL_DIR

echo ""
echo "4. Installing Python dependencies..."
cd $INSTALL_DIR
sudo -u $ACTUAL_USER python3 -m pip install --user -r requirements.txt

echo ""
echo "5. Setting up systemd service..."

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
ExecStart=/usr/bin/python3 $INSTALL_DIR/src/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "6. Enabling and starting service..."
systemctl daemon-reload
systemctl enable meetingbox-ui.service
systemctl start meetingbox-ui.service

echo ""
echo "7. Checking service status..."
sleep 2
systemctl status meetingbox-ui.service --no-pager

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "Service status: systemctl status meetingbox-ui"
echo "View logs: journalctl -u meetingbox-ui -f"
echo "Restart service: systemctl restart meetingbox-ui"
echo ""
