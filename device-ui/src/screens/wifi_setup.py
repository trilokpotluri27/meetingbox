"""
WiFi Setup Screen – Two-column layout

Left  : Step-by-step instructions + I'M CONNECTED button
Right : QR code pointing to http://meetingbox.setup

The actual WiFi hotspot is managed by the host-side onboard service
(scripts/hotspot.sh + scripts/onboard_server.py). This screen reads the
SSID from the hotspot status file or falls back to a generated name.
"""

import subprocess
from pathlib import Path

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock

from screens.base_screen import BaseScreen
from components.button import PrimaryButton
from config import (COLORS, FONT_SIZES, SPACING,
                    HOTSPOT_SSID_PREFIX, HOTSPOT_IP, SETUP_URL)

try:
    import qrcode
    from io import BytesIO
    from kivy.core.image import Image as CoreImage
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


def _get_hotspot_ssid() -> str:
    """Read the active hotspot SSID from the system."""
    # Try reading from hotspot.sh status (runs on host)
    try:
        result = subprocess.run(
            ["bash", "/opt/meetingbox/scripts/hotspot.sh", "status"],
            capture_output=True, text=True, timeout=5,
        )
        parts = result.stdout.strip().split("|")
        if parts[0] == "active" and len(parts) >= 2:
            return parts[1]
    except Exception:
        pass

    # Fallback: derive from MAC address
    try:
        mac = Path("/sys/class/net/wlan0/address").read_text().strip()
        suffix = mac.replace(":", "")[-4:].upper()
        return f"{HOTSPOT_SSID_PREFIX}{suffix}"
    except Exception:
        pass

    return f"{HOTSPOT_SSID_PREFIX}Setup"


class WiFiSetupScreen(BaseScreen):
    """WiFi setup screen shown during first-time configuration."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ssid_label = None
        self._poll_event = None
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(
            orientation='horizontal',
            padding=SPACING['screen_padding'],
            spacing=SPACING['section_spacing'],
        )
        self.make_dark_bg(root)

        # --- LEFT column ---
        left = BoxLayout(
            orientation='vertical',
            size_hint=(0.55, 1),
            spacing=8,
        )

        s1h = Label(
            text='1. Connect to WiFi:',
            font_size=FONT_SIZES['body'],
            color=COLORS['white'],
            halign='left', valign='bottom',
            size_hint=(1, None), height=24,
        )
        s1h.bind(size=s1h.setter('text_size'))
        left.add_widget(s1h)

        ssid = _get_hotspot_ssid()
        self.ssid_label = Label(
            text=f'   {ssid}',
            font_size=FONT_SIZES['medium'],
            bold=True,
            color=COLORS['white'],
            halign='left', valign='top',
            size_hint=(1, None), height=22,
        )
        self.ssid_label.bind(size=self.ssid_label.setter('text_size'))
        left.add_widget(self.ssid_label)

        hint = Label(
            text='   (on your phone or laptop)',
            font_size=FONT_SIZES['small'],
            color=COLORS['gray_500'],
            halign='left',
            size_hint=(1, None), height=18,
        )
        hint.bind(size=hint.setter('text_size'))
        left.add_widget(hint)

        left.add_widget(Widget(size_hint=(1, None), height=8))

        s2h = Label(
            text='2. Open in browser:',
            font_size=FONT_SIZES['body'],
            color=COLORS['white'],
            halign='left', valign='bottom',
            size_hint=(1, None), height=24,
        )
        s2h.bind(size=s2h.setter('text_size'))
        left.add_widget(s2h)

        url_label = Label(
            text=f'   {SETUP_URL}',
            font_size=FONT_SIZES['medium'],
            bold=True,
            color=COLORS['blue'],
            halign='left',
            size_hint=(1, None), height=22,
        )
        url_label.bind(size=url_label.setter('text_size'))
        left.add_widget(url_label)

        left.add_widget(Widget(size_hint=(1, 0.3)))

        btn_row = BoxLayout(size_hint=(1, None), height=60)
        self.connect_btn = PrimaryButton(
            text="I'M CONNECTED  →",
            font_size=FONT_SIZES['medium'],
        )
        self.connect_btn.bind(on_press=self._on_connected)
        btn_row.add_widget(self.connect_btn)
        left.add_widget(btn_row)

        left.add_widget(Widget(size_hint=(1, None), height=8))

        root.add_widget(left)

        # --- RIGHT column: QR code ---
        right = BoxLayout(
            orientation='vertical',
            size_hint=(0.45, 1),
        )

        qr_widget = self._generate_qr(SETUP_URL)
        right.add_widget(qr_widget)
        root.add_widget(right)

        self.add_widget(root)

    def on_enter(self):
        # Refresh SSID and poll for setup completion
        ssid = _get_hotspot_ssid()
        if self.ssid_label:
            self.ssid_label.text = f'   {ssid}'
        self._poll_event = Clock.schedule_interval(self._check_setup_complete, 3.0)

    def on_leave(self):
        if self._poll_event:
            self._poll_event.cancel()
            self._poll_event = None

    def _check_setup_complete(self, _dt):
        """Auto-advance if setup was completed via the web portal."""
        marker_paths = ['/data/config/.setup_complete',
                        '/opt/meetingbox/.setup_complete']
        for p in marker_paths:
            if Path(p).exists():
                self.goto('all_set', transition='fade')
                return

    def _generate_qr(self, url: str):
        """Generate QR code image widget."""
        if HAS_QRCODE:
            try:
                qr = qrcode.QRCode(version=1, box_size=6, border=1)
                qr.add_data(url)
                qr.make(fit=True)
                img = qr.make_image(fill_color='white', back_color='black')
                buf = BytesIO()
                img.save(buf, format='PNG')
                buf.seek(0)
                core_img = CoreImage(buf, ext='png')
                return Image(texture=core_img.texture, size_hint=(1, 1))
            except Exception:
                pass
        lbl = Label(
            text='[QR CODE]',
            font_size=FONT_SIZES['large'],
            color=COLORS['gray_500'],
        )
        return lbl

    def _on_connected(self, _inst):
        self.goto('setup_progress', transition='fade')
