#!/usr/bin/env bash
# ============================================================================
# MeetingBox WiFi Hotspot Manager
#
# Uses NetworkManager (nmcli) to create/destroy a WiFi access point.
# The hotspot runs a DHCP server automatically via NM's shared mode.
#
# Usage:
#   sudo bash hotspot.sh start [SSID_SUFFIX]   # Start hotspot
#   sudo bash hotspot.sh stop                    # Stop and restore WiFi
#   sudo bash hotspot.sh status                  # Show hotspot state
# ============================================================================

set -euo pipefail

CON_NAME="MeetingBox-Hotspot"
SSID_PREFIX="MeetingBox-"
HOTSPOT_IP="192.168.4.1"
WIFI_IFACE="${WIFI_IFACE:-wlan0}"

get_suffix() {
    # Use last 4 chars of wlan0 MAC as suffix, or fallback
    local mac
    mac=$(cat "/sys/class/net/${WIFI_IFACE}/address" 2>/dev/null || echo "00:00:00:00:00:00")
    echo "${mac//:/}" | tail -c 5 | tr '[:lower:]' '[:upper:]'
}

cmd_start() {
    local suffix="${1:-$(get_suffix)}"
    local ssid="${SSID_PREFIX}${suffix}"

    echo "[Hotspot] Starting access point: ${ssid}"

    # Remove any previous hotspot connection profile
    nmcli connection delete "$CON_NAME" 2>/dev/null || true

    # Create WiFi hotspot (no password — open network for easy onboarding)
    nmcli connection add \
        type wifi \
        ifname "$WIFI_IFACE" \
        con-name "$CON_NAME" \
        autoconnect no \
        ssid "$ssid" \
        -- \
        wifi.mode ap \
        wifi.band bg \
        wifi.channel 6 \
        ipv4.method shared \
        ipv4.addresses "${HOTSPOT_IP}/24" \
        ipv6.method disabled

    nmcli connection up "$CON_NAME"

    # Add DNS redirect so meetingbox.setup resolves to our IP.
    # dnsmasq is started automatically by NM in shared mode;
    # we write a drop-in config to redirect our domain.
    local dnsmasq_conf="/etc/NetworkManager/dnsmasq-shared.d/meetingbox.conf"
    mkdir -p "$(dirname "$dnsmasq_conf")"
    cat > "$dnsmasq_conf" <<EOF
address=/meetingbox.setup/${HOTSPOT_IP}
address=/meetingbox.local/${HOTSPOT_IP}
EOF

    # Restart NM's dnsmasq to pick up the config
    nmcli connection down "$CON_NAME" 2>/dev/null || true
    sleep 1
    nmcli connection up "$CON_NAME"

    echo "[Hotspot] AP active — SSID: ${ssid}, IP: ${HOTSPOT_IP}"
    echo "[Hotspot] meetingbox.setup → ${HOTSPOT_IP}"
}

cmd_stop() {
    echo "[Hotspot] Stopping access point..."
    nmcli connection down "$CON_NAME" 2>/dev/null || true
    nmcli connection delete "$CON_NAME" 2>/dev/null || true

    # Clean up DNS redirect
    rm -f /etc/NetworkManager/dnsmasq-shared.d/meetingbox.conf

    echo "[Hotspot] AP stopped. WiFi will reconnect to previous network."
}

cmd_status() {
    if nmcli -t connection show --active | grep -q "$CON_NAME"; then
        local ssid
        ssid=$(nmcli -t -f 802-11-wireless.ssid connection show "$CON_NAME" 2>/dev/null | cut -d: -f2)
        echo "active|${ssid}|${HOTSPOT_IP}"
    else
        echo "inactive"
    fi
}

case "${1:-help}" in
    start)  cmd_start "${2:-}" ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    *)
        echo "Usage: sudo bash $0 {start [SUFFIX]|stop|status}"
        exit 1
        ;;
esac
