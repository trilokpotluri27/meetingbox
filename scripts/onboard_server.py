#!/usr/bin/env python3
"""
MeetingBox Onboarding Server

Lightweight HTTP server that runs on the HOST (not in Docker) during first-time
setup. Serves a WiFi configuration page on port 80 so users can connect via
the MeetingBox hotspot and enter their home WiFi credentials.

Flow:
  1. systemd starts this + hotspot on first boot (no .setup_complete marker)
  2. User connects phone to MeetingBox-XXXX hotspot
  3. Phone opens http://meetingbox.setup (DNS redirected to 192.168.4.1)
  4. User submits WiFi SSID + password
  5. This server connects the Pi to that WiFi, marks setup complete, stops itself

Run: sudo python3 scripts/onboard_server.py
"""

import http.server
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

LISTEN_PORT = 80
SETUP_MARKER = "/data/config/.setup_complete"
HOTSPOT_SCRIPT = os.path.join(os.path.dirname(__file__), "hotspot.sh")

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MeetingBox Setup</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #1C1C1E; color: #fff; min-height: 100vh;
    display: flex; justify-content: center; align-items: center;
    padding: 20px;
  }
  .card {
    background: #2C2C2E; border-radius: 16px; padding: 32px;
    max-width: 400px; width: 100%; box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  }
  h1 { font-size: 24px; text-align: center; margin-bottom: 8px; }
  .subtitle { color: #8E8E93; text-align: center; margin-bottom: 24px; font-size: 14px; }
  label { display: block; color: #AEAEB2; font-size: 13px; margin-bottom: 6px; margin-top: 16px; }
  input[type=text], input[type=password] {
    width: 100%; padding: 12px 16px; border-radius: 10px;
    border: 1px solid #545458; background: #1C1C1E; color: #fff;
    font-size: 16px; outline: none;
  }
  input:focus { border-color: #3888FA; }
  .btn {
    width: 100%; padding: 14px; border: none; border-radius: 12px;
    background: linear-gradient(135deg, #3888FA, #2273F5);
    color: #fff; font-size: 17px; font-weight: 600;
    cursor: pointer; margin-top: 24px;
  }
  .btn:active { opacity: 0.8; }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .status { text-align: center; margin-top: 16px; font-size: 14px; color: #8E8E93; }
  .status.error { color: #FF453A; }
  .status.success { color: #34C759; }
  .scan-list { max-height: 200px; overflow-y: auto; margin-top: 8px; }
  .scan-item {
    padding: 10px 14px; background: #1C1C1E; border-radius: 8px;
    margin-bottom: 6px; cursor: pointer; display: flex;
    justify-content: space-between; align-items: center;
  }
  .scan-item:hover { background: #38383A; }
  .scan-item .signal { color: #8E8E93; font-size: 12px; }
  .loader { display: none; text-align: center; padding: 20px; }
  .loader.active { display: block; }
</style>
</head>
<body>
<div class="card">
  <h1>MeetingBox Setup</h1>
  <p class="subtitle">Connect your MeetingBox to WiFi</p>

  <div id="scan-section">
    <label>Available Networks</label>
    <div id="scan-list" class="scan-list"></div>
    <div id="scan-loader" class="loader active">Scanning for networks...</div>
  </div>

  <form id="wifi-form" onsubmit="return submitWifi(event)">
    <label for="ssid">WiFi Network Name</label>
    <input type="text" id="ssid" name="ssid" required placeholder="Select from above or type manually">

    <label for="password">WiFi Password</label>
    <input type="password" id="password" name="password" placeholder="Enter password">

    <button type="submit" class="btn" id="connect-btn">Connect</button>
  </form>

  <div id="status" class="status"></div>
</div>

<script>
async function scanNetworks() {
  try {
    const res = await fetch('/api/scan');
    const networks = await res.json();
    const list = document.getElementById('scan-list');
    document.getElementById('scan-loader').classList.remove('active');
    if (networks.length === 0) {
      list.innerHTML = '<div class="scan-item">No networks found</div>';
      return;
    }
    list.innerHTML = '';
    networks.forEach(n => {
      const div = document.createElement('div');
      div.className = 'scan-item';
      div.innerHTML = '<span>' + n.ssid + '</span><span class="signal">' + n.signal + '%</span>';
      div.onclick = () => { document.getElementById('ssid').value = n.ssid; };
      list.appendChild(div);
    });
  } catch(e) {
    document.getElementById('scan-loader').textContent = 'Scan failed — enter network name manually';
    document.getElementById('scan-loader').classList.add('active');
  }
}

async function submitWifi(e) {
  e.preventDefault();
  const ssid = document.getElementById('ssid').value;
  const password = document.getElementById('password').value;
  const status = document.getElementById('status');
  const btn = document.getElementById('connect-btn');

  btn.disabled = true;
  btn.textContent = 'Connecting...';
  status.className = 'status';
  status.textContent = 'Connecting to ' + ssid + '...';

  try {
    const res = await fetch('/api/connect', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ssid, password})
    });
    const data = await res.json();
    if (data.status === 'connected') {
      status.className = 'status success';
      status.textContent = 'Connected! MeetingBox is setting up — you can close this page.';
      btn.textContent = 'Done!';
    } else {
      status.className = 'status error';
      status.textContent = data.message || 'Connection failed. Check password and try again.';
      btn.disabled = false;
      btn.textContent = 'Connect';
    }
  } catch(e) {
    status.className = 'status error';
    status.textContent = 'Connection lost — MeetingBox may be connecting to your WiFi. Check the device screen.';
  }
}

scanNetworks();
</script>
</body>
</html>
"""


class OnboardHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[Onboard] {args[0]}", flush=True)

    def do_GET(self):
        if self.path == "/api/scan":
            self._handle_scan()
        else:
            self._serve_page()

    def do_POST(self):
        if self.path == "/api/connect":
            self._handle_connect()
        else:
            self.send_error(404)

    def _serve_page(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode())

    def _handle_scan(self):
        networks = []
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"],
                capture_output=True, text=True, timeout=15,
            )
            seen = set()
            for line in result.stdout.strip().splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and parts[0] and parts[0] not in seen:
                    if parts[0].startswith("MeetingBox-"):
                        continue  # Don't show our own hotspot
                    seen.add(parts[0])
                    networks.append({
                        "ssid": parts[0],
                        "signal": int(parts[1]) if parts[1].isdigit() else 0,
                        "security": parts[2] or "open",
                    })
            networks.sort(key=lambda n: n["signal"], reverse=True)
        except Exception as e:
            print(f"[Onboard] Scan error: {e}", flush=True)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(networks).encode())

    def _handle_connect(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        ssid = body.get("ssid", "")
        password = body.get("password", "")

        if not ssid:
            self._json_response({"status": "failed", "message": "No SSID provided"})
            return

        print(f"[Onboard] Connecting to WiFi: {ssid}", flush=True)

        try:
            cmd = ["nmcli", "dev", "wifi", "connect", ssid]
            if password:
                cmd += ["password", password]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print(f"[Onboard] WiFi connected to {ssid}", flush=True)
                self._json_response({"status": "connected"})

                # Mark setup as complete
                marker = Path(SETUP_MARKER)
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text("1")
                print(f"[Onboard] Setup marker written: {SETUP_MARKER}", flush=True)

                # Stop the hotspot (in background, after response is sent)
                subprocess.Popen(
                    ["bash", HOTSPOT_SCRIPT, "stop"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                print("[Onboard] Hotspot stop scheduled — onboarding complete", flush=True)
            else:
                msg = result.stderr.strip() or "Connection failed"
                print(f"[Onboard] WiFi failed: {msg}", flush=True)
                self._json_response({"status": "failed", "message": msg})

        except Exception as e:
            print(f"[Onboard] Error: {e}", flush=True)
            self._json_response({"status": "failed", "message": str(e)})

    def _json_response(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def main():
    marker = Path(SETUP_MARKER)
    if marker.exists():
        print("[Onboard] Setup already complete — exiting", flush=True)
        sys.exit(0)

    print(f"[Onboard] Starting onboarding server on port {LISTEN_PORT}", flush=True)
    server = http.server.HTTPServer(("0.0.0.0", LISTEN_PORT), OnboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("[Onboard] Server stopped", flush=True)


if __name__ == "__main__":
    main()
