"""
WiFi Settings Screen

Landscape: compact network list.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.clock import Clock
from async_helper import run_async

from screens.base_screen import BaseScreen
from components.status_bar import StatusBar
from components.wifi_network_item import WiFiNetworkItem
from components.button import SecondaryButton
from config import COLORS, FONT_SIZES, SPACING


class WiFiScreen(BaseScreen):
    """WiFi settings — landscape 480x320."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.networks = []
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical')
        
        self.status_bar = StatusBar(
            status_text='<- BACK',
            device_name='WiFi',
            back_button=True,
            on_back=self.go_back
        )
        layout.add_widget(self.status_bar)
        
        # Horizontal: network list left, scan button right
        content = BoxLayout(
            orientation='horizontal',
            padding=SPACING['screen_padding'],
            spacing=SPACING['section_spacing']
        )
        
        # Left: current + networks
        left = BoxLayout(
            orientation='vertical',
            size_hint=(0.7, 1),
            spacing=SPACING['button_spacing']
        )
        
        self.current_label = Label(
            text='Current: Loading...',
            font_size=FONT_SIZES['tiny'],
            size_hint=(1, None), height=14,
            color=COLORS['gray_700'], halign='left'
        )
        self.current_label.bind(size=self.current_label.setter('text_size'))
        left.add_widget(self.current_label)
        
        scroll = ScrollView(size_hint=(1, 1))
        self.networks_container = GridLayout(
            cols=1,
            spacing=SPACING['list_item_spacing'],
            size_hint_y=None
        )
        self.networks_container.bind(minimum_height=self.networks_container.setter('height'))
        scroll.add_widget(self.networks_container)
        left.add_widget(scroll)
        
        content.add_widget(left)
        
        # Right: scan button
        right = BoxLayout(
            orientation='vertical',
            size_hint=(0.3, 1),
            spacing=SPACING['button_spacing']
        )
        right.add_widget(Label(size_hint=(1, 0.6)))  # spacer
        scan_btn = SecondaryButton(text='SCAN', size_hint=(1, 0.35))
        scan_btn.bind(on_press=self.on_scan_pressed)
        right.add_widget(scan_btn)
        
        content.add_widget(right)
        layout.add_widget(content)
        self.add_widget(layout)
    
    def on_enter(self):
        self.load_networks()
    
    def load_networks(self):
        async def _load():
            try:
                networks = await self.backend.get_wifi_networks()
                self.networks = networks
                Clock.schedule_once(lambda dt: self.populate_networks(), 0)
            except Exception as e:
                print(f"Failed to load WiFi networks: {e}")
        run_async(_load())
    
    def populate_networks(self):
        self.networks_container.clear_widgets()
        current = next((n for n in self.networks if n.get('connected')), None)
        if current:
            self.current_label.text = f"Current: {current['ssid']}"
        else:
            self.current_label.text = "Not connected"
        
        for network in self.networks:
            item = WiFiNetworkItem(network=network)
            item.bind(on_press=self.on_network_pressed)
            self.networks_container.add_widget(item)
    
    def on_network_pressed(self, instance):
        network = instance.network
        if network.get('connected'):
            return
        self.connect_to_network(network['ssid'])
    
    def connect_to_network(self, ssid: str, password: str = None):
        async def _connect():
            try:
                result = await self.backend.connect_wifi(ssid, password)
                if result.get('status') == 'connected':
                    Clock.schedule_once(lambda dt: self.load_networks(), 0)
            except Exception as e:
                print(f"Failed to connect to {ssid}: {e}")
        run_async(_connect())
    
    def on_scan_pressed(self, instance):
        self.load_networks()
