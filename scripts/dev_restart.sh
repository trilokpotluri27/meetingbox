#!/bin/bash
# ============================================================================
# MeetingBox Dev Restart
#
# Single command to pull latest code, rebuild, and start everything fresh
# including the OLED screen UI and onboarding hotspot.
#
# Usage:
#   cd ~/meetingbox && sudo bash scripts/dev_restart.sh
#
# Options:
#   --fresh    Reset onboarding (remove .setup_complete marker)
#   --no-build Skip Docker image rebuild (faster if only config changed)
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

FRESH=false
BUILD=true

for arg in "$@"; do
    case $arg in
        --fresh)   FRESH=true ;;
        --no-build) BUILD=false ;;
    esac
done

echo "=========================================="
echo "  MeetingBox Dev Restart"
echo "=========================================="
echo "  Project: $PROJECT_DIR"
echo "  Fresh onboarding: $FRESH"
echo "  Rebuild images: $BUILD"
echo ""

# 1. Stop everything
echo "[1/7] Stopping containers..."
docker stop meetingbox-ui 2>/dev/null || true
docker rm meetingbox-ui 2>/dev/null || true
docker compose --profile screen down 2>/dev/null || true
sudo pkill -f onboard_server 2>/dev/null || true
sudo bash scripts/hotspot.sh stop 2>/dev/null || true

# 2. Pull latest code
echo "[2/7] Pulling latest code..."
ACTUAL_USER=${SUDO_USER:-$USER}
sudo -u "$ACTUAL_USER" git pull || echo "   (git pull skipped — not a git issue)"

# 3. Fresh onboarding reset
if [ "$FRESH" = true ]; then
    echo "[3/7] Resetting onboarding state..."
    rm -f "$PROJECT_DIR/data/config/.setup_complete"
    rm -f /opt/meetingbox/data/config/.setup_complete 2>/dev/null || true
else
    echo "[3/7] Keeping existing setup state"
fi

# 4. Rebuild if needed
if [ "$BUILD" = true ]; then
    echo "[4/7] Building Docker images..."
    docker compose --profile screen build
else
    echo "[4/7] Skipping build (--no-build)"
fi

# 5. Start backend services
echo "[5/7] Starting backend services..."
docker compose up -d
sleep 5

# 6. X11 access
echo "[6/7] Granting X11 access..."
DISPLAY=:0 xhost +local: 2>/dev/null || echo "   (xhost not available — run startx first)"

# 7. Start screen UI + onboarding
echo "[7/7] Starting device UI..."
docker compose --profile screen up -d device-ui

MARKER="$PROJECT_DIR/data/config/.setup_complete"
if [ ! -f "$MARKER" ]; then
    echo "       Starting onboarding hotspot + server..."
    sudo bash scripts/hotspot.sh start
    sudo python3 scripts/onboard_server.py &
    echo "       Hotspot active — connect phone to MeetingBox WiFi"
fi

echo ""
echo "=========================================="
echo "  All running!"
echo "=========================================="
echo ""
echo "  UI logs:     docker logs -f meetingbox-ui 2>&1"
echo "  All logs:    docker compose logs -f"
echo "  Stop all:    docker compose --profile screen down"
echo ""
if [ ! -f "$MARKER" ]; then
    echo "  ONBOARDING: Connect phone to MeetingBox hotspot"
    echo "              Open http://192.168.4.1 in browser"
fi
echo ""
