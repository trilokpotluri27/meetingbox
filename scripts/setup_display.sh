#!/bin/bash
# Configure display for Raspberry Pi with OLED touchscreen
#
# NOTE: This script is for PRODUCTION use only (when the
# physical screen is connected). Do NOT run during development.
#
# During dev, the device-ui runs in windowed mode via:
#   docker compose --profile screen up -d device-ui

set -e

echo "Configuring display for MeetingBox..."
echo ""
echo "WARNING: This enables auto-start X11 on boot."
echo "Only run this when the physical screen is connected."
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Detect display resolution
DISPLAY_WIDTH=${DISPLAY_WIDTH:-480}
DISPLAY_HEIGHT=${DISPLAY_HEIGHT:-800}

echo "Display resolution: ${DISPLAY_WIDTH}x${DISPLAY_HEIGHT}"

# Configure X11
mkdir -p /etc/X11/xorg.conf.d

cat > /etc/X11/xorg.conf.d/99-meetingbox-display.conf << EOF
Section "Monitor"
    Identifier "OLED"
    Option "PreferredMode" "${DISPLAY_WIDTH}x${DISPLAY_HEIGHT}"
EndSection

Section "Screen"
    Identifier "Default Screen"
    Monitor "OLED"
    DefaultDepth 24
EndSection
EOF

# Auto-start X on boot
if ! grep -q "startx" /home/meetingbox/.bashrc; then
    echo "if [ -z \"\$DISPLAY\" ] && [ \$(tty) = /dev/tty1 ]; then startx; fi" >> /home/meetingbox/.bashrc
fi

# Create .xinitrc to start UI
cat > /home/meetingbox/.xinitrc << 'EOF'
#!/bin/sh
# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Allow Docker containers to draw on this display
xhost +local:

# Hide cursor
unclutter -idle 0 &

# Keep X running (Docker device-ui container draws on this display)
while true; do
    sleep 1
done
EOF

chmod +x /home/meetingbox/.xinitrc
chown meetingbox:meetingbox /home/meetingbox/.xinitrc

echo "Display configuration complete!"
echo "Reboot to apply changes: sudo reboot"
