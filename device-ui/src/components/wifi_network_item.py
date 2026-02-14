"""
WiFi Network Item Component

Row showing WiFi network info.
"""

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from config import COLORS, FONT_SIZES, SPACING


class WiFiNetworkItem(ButtonBehavior, BoxLayout):
    """
    WiFi network item.
    
    Shows:
    - SSID
    - Signal strength (bars)
    - Connected status
    - Lock icon (if secured)
    """
    
    def __init__(self, network: dict, **kwargs):
        self.network = network
        
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', 40)
        kwargs.setdefault('padding', SPACING['button_spacing'])
        kwargs.setdefault('spacing', 4)
        
        super().__init__(**kwargs)
        
        # Background
        with self.canvas.before:
            Color(*COLORS['white'])
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        # SSID
        ssid_label = Label(
            text=network['ssid'],
            font_size=FONT_SIZES['medium'],
            color=COLORS['gray_900'],
            bold=network.get('connected', False),
            halign='left',
            size_hint=(0.7, 1)
        )
        ssid_label.bind(size=ssid_label.setter('text_size'))
        self.add_widget(ssid_label)
        
        # Signal strength
        signal = network.get('signal_strength', 0)
        bars_count = max(1, signal // 25)
        bars = '|' * bars_count
        
        signal_label = Label(
            text=bars,
            font_size=FONT_SIZES['medium'],
            color=COLORS['blue'] if network.get('connected') else COLORS['gray_600'],
            size_hint=(0.2, 1)
        )
        self.add_widget(signal_label)
        
        # Connected indicator
        if network.get('connected'):
            status_label = Label(
                text='OK',
                font_size=FONT_SIZES['medium'],
                color=COLORS['green'],
                size_hint=(0.1, 1)
            )
            self.add_widget(status_label)
        
        # Bottom border
        with self.canvas.after:
            Color(*COLORS['gray_200'])
            self.border = Rectangle(
                pos=(self.x, self.y),
                size=(self.width, 1)
            )
        
        self.bind(pos=self._update_border, size=self._update_border)
    
    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
    
    def _update_border(self, *args):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(*COLORS['gray_200'])
            self.border = Rectangle(
                pos=(self.x, self.y),
                size=(self.width, 1)
            )
    
    def on_press(self):
        """Highlight on press"""
        if not self.network.get('connected'):
            self.canvas.before.clear()
            with self.canvas.before:
                Color(*COLORS['blue_50'])
                self.bg_rect = Rectangle(pos=self.pos, size=self.size)
    
    def on_release(self):
        """Restore on release"""
        self._update_bg()
