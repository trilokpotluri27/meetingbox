#!/bin/bash
# Configure display for Raspberry Pi with OLED touchscreen

set -e

echo "Configuring display for MeetingBox..."

# Detect display resolution
# This is a placeholder - actual detection depends on hardware
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

# Hide cursor
unclutter -idle 0 &

# Start MeetingBox UI (systemd will handle this)
# Just keep X running
while true; do
    sleep 1
done
EOF

chmod +x /home/meetingbox/.xinitrc
chown meetingbox:meetingbox /home/meetingbox/.xinitrc

echo "Display configuration complete!"
echo "Reboot to apply changes: sudo reboot"
