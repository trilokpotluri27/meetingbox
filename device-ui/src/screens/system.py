"""
System Info Screen

Landscape: info left, update button right.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from async_helper import run_async

from screens.base_screen import BaseScreen
from components.status_bar import StatusBar
from components.button import PrimaryButton
from config import COLORS, FONT_SIZES, SPACING


class SystemScreen(BaseScreen):
    """System info — landscape 480x320."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system_info = {}
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical')
        
        self.status_bar = StatusBar(
            status_text='<- BACK',
            device_name='System',
            back_button=True,
            on_back=self.go_back
        )
        layout.add_widget(self.status_bar)
        
        # Horizontal: info left, update btn right
        content = BoxLayout(
            orientation='horizontal',
            padding=SPACING['screen_padding'],
            spacing=SPACING['section_spacing']
        )
        
        # Left: scrollable info
        scroll = ScrollView(size_hint=(0.65, 1))
        self.info_label = Label(
            text='Loading...',
            font_size=FONT_SIZES['small'],
            size_hint_y=None,
            color=COLORS['gray_700'],
            halign='left', valign='top'
        )
        self.info_label.bind(texture_size=self.info_label.setter('size'))
        self.info_label.bind(size=self.info_label.setter('text_size'))
        scroll.add_widget(self.info_label)
        content.add_widget(scroll)
        
        # Right: update button
        right = BoxLayout(
            orientation='vertical',
            size_hint=(0.35, 1),
            spacing=SPACING['button_spacing']
        )
        right.add_widget(Label(size_hint=(1, 0.5)))  # spacer
        self.update_btn = PrimaryButton(
            text='CHECK\nUPDATES',
            size_hint=(1, 0.4)
        )
        self.update_btn.bind(on_press=self.on_update_pressed)
        right.add_widget(self.update_btn)
        
        content.add_widget(right)
        layout.add_widget(content)
        self.add_widget(layout)
    
    def on_enter(self):
        self.load_system_info()
    
    def load_system_info(self):
        async def _load():
            try:
                info = await self.backend.get_system_info()
                self.system_info = info
                Clock.schedule_once(lambda dt: self.populate_info(), 0)
            except Exception as e:
                print(f"Failed to load system info: {e}")
        run_async(_load())
    
    def populate_info(self):
        if not self.system_info:
            return
        su = self.system_info.get('storage_used', 0) / (1024**3)
        st = self.system_info.get('storage_total', 1) / (1024**3)
        sf = st - su
        up_s = self.system_info.get('uptime', 0)
        up_h = up_s // 3600
        up_d = up_h // 24
        sig = self.system_info.get('wifi_signal', 0)
        bars = '|' * max(1, sig // 25)
        
        self.info_label.text = (
            f"Name: {self.system_info.get('device_name', '?')}\n"
            f"IP: {self.system_info.get('ip_address', '?')}\n"
            f"WiFi: {self.system_info.get('wifi_ssid', 'N/A')} {bars}\n"
            f"Storage: {su:.0f}/{st:.0f}GB ({sf:.0f}GB free)\n"
            f"Meetings: {self.system_info.get('meetings_count', 0)}\n"
            f"Firmware: {self.system_info.get('firmware_version', '?')}\n"
            f"Uptime: {up_d}d {up_h % 24}h"
        )
    
    def on_update_pressed(self, instance):
        async def _check():
            try:
                self.update_btn.text = 'Checking...'
                self.update_btn.disabled = True
                result = await self.backend.check_for_updates()
                if result.get('update_available'):
                    v = result.get('latest_version')
                    Clock.schedule_once(lambda dt: setattr(self.update_btn, 'text', f'Install {v}'), 0)
                else:
                    Clock.schedule_once(lambda dt: setattr(self.update_btn, 'text', 'Up to date'), 0)
                    Clock.schedule_once(lambda dt: self._reset_update_button(), 2.0)
            except Exception as e:
                print(f"Check failed: {e}")
                Clock.schedule_once(lambda dt: setattr(self.update_btn, 'text', 'Failed'), 0)
                Clock.schedule_once(lambda dt: self._reset_update_button(), 2.0)
            finally:
                Clock.schedule_once(lambda dt: setattr(self.update_btn, 'disabled', False), 0)
        run_async(_check())
    
    def _reset_update_button(self):
        self.update_btn.text = 'CHECK\nUPDATES'
