"""
WiFi Setup Screen – Two-column layout

Left  : Step-by-step instructions + I'M CONNECTED button
Right : QR code pointing to http://meetingbox.setup
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle

from screens.base_screen import BaseScreen
from components.button import PrimaryButton
from config import (COLORS, FONT_SIZES, SPACING,
                    HOTSPOT_SSID_PREFIX, SETUP_URL)

try:
    import qrcode
    from io import BytesIO
    from kivy.core.image import Image as CoreImage
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


class WiFiSetupScreen(BaseScreen):
    """WiFi setup screen shown during first-time configuration."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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

        # Step 1
        s1h = Label(
            text='1. Connect to WiFi:',
            font_size=FONT_SIZES['body'],
            color=COLORS['white'],
            halign='left', valign='bottom',
            size_hint=(1, None), height=24,
        )
        s1h.bind(size=s1h.setter('text_size'))
        left.add_widget(s1h)

        ssid_suffix = 'A1B2'  # placeholder – replaced at runtime from MAC
        ssid_label = Label(
            text=f'   {HOTSPOT_SSID_PREFIX}{ssid_suffix}',
            font_size=FONT_SIZES['medium'],
            bold=True,
            color=COLORS['white'],
            halign='left', valign='top',
            size_hint=(1, None), height=22,
        )
        ssid_label.bind(size=ssid_label.setter('text_size'))
        left.add_widget(ssid_label)

        hint = Label(
            text='   (through phone or PC)',
            font_size=FONT_SIZES['small'],
            color=COLORS['gray_500'],
            halign='left',
            size_hint=(1, None), height=18,
        )
        hint.bind(size=hint.setter('text_size'))
        left.add_widget(hint)

        left.add_widget(Widget(size_hint=(1, None), height=8))

        # Step 2
        s2h = Label(
            text='2. Open browser:',
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
            color=COLORS['white'],
            halign='left',
            size_hint=(1, None), height=22,
        )
        url_label.bind(size=url_label.setter('text_size'))
        left.add_widget(url_label)

        # Spacer
        left.add_widget(Widget(size_hint=(1, 0.3)))

        # I'M CONNECTED button
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

        qr_widget = self._generate_qr(f'http://{SETUP_URL}')
        right.add_widget(qr_widget)
        root.add_widget(right)

        self.add_widget(root)

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
        # Fallback placeholder
        lbl = Label(
            text='[QR CODE]',
            font_size=FONT_SIZES['large'],
            color=COLORS['gray_500'],
        )
        return lbl

    def _on_connected(self, _inst):
        self.goto('setup_progress', transition='fade')
