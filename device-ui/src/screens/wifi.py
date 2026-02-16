"""
WiFi Settings Screen – Dark themed (480 × 320)

Compact network list with scan button.
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
    """WiFi settings – dark theme."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.networks = []
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical')
        self.make_dark_bg(root)

        self.status_bar = StatusBar(
            status_text='WiFi',
            device_name='WiFi',
            back_button=True,
            on_back=self.go_back,
            show_settings=False,
        )
        root.add_widget(self.status_bar)

        content = BoxLayout(
            orientation='horizontal',
            padding=SPACING['screen_padding'],
            spacing=SPACING['section_spacing'],
        )

        left = BoxLayout(orientation='vertical', size_hint=(0.7, 1), spacing=SPACING['button_spacing'])

        self.current_label = Label(
            text='Current: Loading…',
            font_size=FONT_SIZES['small'],
            size_hint=(1, None), height=18,
            color=COLORS['gray_400'], halign='left',
        )
        self.current_label.bind(size=self.current_label.setter('text_size'))
        left.add_widget(self.current_label)

        scroll = ScrollView(do_scroll_x=False)
        self.networks_container = GridLayout(
            cols=1, spacing=SPACING['list_item_spacing'], size_hint_y=None)
        self.networks_container.bind(
            minimum_height=self.networks_container.setter('height'))
        scroll.add_widget(self.networks_container)
        left.add_widget(scroll)

        content.add_widget(left)

        right = BoxLayout(orientation='vertical', size_hint=(0.3, 1),
                          spacing=SPACING['button_spacing'])
        from kivy.uix.widget import Widget
        right.add_widget(Widget(size_hint=(1, 0.6)))
        scan_btn = SecondaryButton(text='SCAN', size_hint=(1, 0.35))
        scan_btn.bind(on_press=lambda _: self._load_networks())
        right.add_widget(scan_btn)
        content.add_widget(right)

        root.add_widget(content)

        footer = self.build_footer()
        root.add_widget(footer)

        self.add_widget(root)

    def on_enter(self):
        self._load_networks()

    def _load_networks(self):
        async def _load():
            try:
                nets = await self.backend.get_wifi_networks()
                self.networks = nets
                Clock.schedule_once(lambda _: self._populate(), 0)
            except Exception:
                pass
        run_async(_load())

    def _populate(self):
        self.networks_container.clear_widgets()
        current = next((n for n in self.networks if n.get('connected')), None)
        self.current_label.text = f"Current: {current['ssid']}" if current else 'Not connected'
        for net in self.networks:
            item = WiFiNetworkItem(network=net)
            item.bind(on_press=self._on_network)
            self.networks_container.add_widget(item)

    def _on_network(self, instance):
        if instance.network.get('connected'):
            return
        async def _connect():
            try:
                result = await self.backend.connect_wifi(instance.network['ssid'])
                if result.get('status') == 'connected':
                    Clock.schedule_once(lambda _: self._load_networks(), 0)
            except Exception:
                pass
        run_async(_connect())
