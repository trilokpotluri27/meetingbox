"""
Setup Screen

Landscape: instructions left, QR code right.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.clock import Clock
import qrcode
from pathlib import Path

from screens.base_screen import BaseScreen
from components.button import PrimaryButton
from config import COLORS, FONT_SIZES, SPACING


class SetupScreen(BaseScreen):
    """Setup screen — landscape 480x320."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        # Horizontal split: instructions left, QR right
        layout = BoxLayout(
            orientation='horizontal',
            padding=SPACING['screen_padding'],
            spacing=SPACING['section_spacing']
        )
        
        # Left: instructions
        left = BoxLayout(
            orientation='vertical',
            size_hint=(0.55, 1),
            spacing=SPACING['button_spacing']
        )
        
        header = Label(
            text='SETUP REQUIRED',
            font_size=FONT_SIZES['large'],
            size_hint=(1, 0.15),
            color=COLORS['gray_900'],
            bold=True,
            halign='left'
        )
        header.bind(size=header.setter('text_size'))
        left.add_widget(header)
        
        wifi_label = Label(
            text='1. Connect to WiFi:',
            font_size=FONT_SIZES['small'],
            size_hint=(1, 0.1),
            color=COLORS['gray_700'],
            halign='left'
        )
        wifi_label.bind(size=wifi_label.setter('text_size'))
        left.add_widget(wifi_label)
        
        wifi_ssid = Label(
            text='  MeetingBox-A1B2',
            font_size=FONT_SIZES['medium'],
            bold=True,
            size_hint=(1, 0.12),
            color=COLORS['blue'],
            halign='left'
        )
        wifi_ssid.bind(size=wifi_ssid.setter('text_size'))
        left.add_widget(wifi_ssid)
        
        url_label = Label(
            text='2. Open in browser:',
            font_size=FONT_SIZES['small'],
            size_hint=(1, 0.1),
            color=COLORS['gray_700'],
            halign='left'
        )
        url_label.bind(size=url_label.setter('text_size'))
        left.add_widget(url_label)
        
        url = Label(
            text='  meetingbox.setup\n  or 192.168.4.1',
            font_size=FONT_SIZES['small'],
            size_hint=(1, 0.2),
            color=COLORS['gray_900'],
            halign='left',
            valign='top'
        )
        url.bind(size=url.setter('text_size'))
        left.add_widget(url)
        
        scan_btn = PrimaryButton(
            text='SCAN TO SETUP ->',
            size_hint=(1, 0.2)
        )
        scan_btn.bind(on_press=self.on_scan_pressed)
        left.add_widget(scan_btn)
        
        layout.add_widget(left)
        
        # Right: QR code
        qr_image = self.generate_qr_code('http://meetingbox.setup')
        layout.add_widget(qr_image)
        
        self.add_widget(layout)
        
        Clock.schedule_interval(self.check_setup_complete, 2.0)
    
    def generate_qr_code(self, url: str):
        qr = qrcode.QRCode(version=1, box_size=6, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        # Simplified — in production save to temp file and load
        img_widget = Image(size_hint=(0.45, 1))
        return img_widget
    
    def on_scan_pressed(self, instance):
        pass
    
    def check_setup_complete(self, dt):
        if Path('/opt/meetingbox/.setup_complete').exists():
            self.goto('home')
            return False
        return True
