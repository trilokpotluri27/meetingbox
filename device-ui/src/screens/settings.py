"""
Settings Menu Screen

Landscape: compact list of settings items.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

from screens.base_screen import BaseScreen
from components.status_bar import StatusBar
from components.settings_item import SettingsItem
from config import SPACING


class SettingsScreen(BaseScreen):
    """Settings menu — landscape 480x320."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical')
        
        self.status_bar = StatusBar(
            status_text='<- BACK',
            device_name='Settings',
            back_button=True,
            on_back=self.go_back
        )
        layout.add_widget(self.status_bar)
        
        scroll = ScrollView()
        items_container = GridLayout(
            cols=1,
            spacing=SPACING['list_item_spacing'],
            padding=SPACING['screen_padding'],
            size_hint_y=None
        )
        items_container.bind(minimum_height=items_container.setter('height'))
        
        wifi_item = SettingsItem(
            title='WiFi',
            subtitle='Conference-Network',
            on_press=lambda x: self.goto('wifi')
        )
        items_container.add_widget(wifi_item)
        
        device_item = SettingsItem(
            title='Device Name',
            subtitle='Conference Room A',
            on_press=self.on_device_name_pressed
        )
        items_container.add_widget(device_item)
        
        integrations_item = SettingsItem(
            title='Integrations',
            subtitle='Gmail, Calendar',
            on_press=self.on_integrations_pressed
        )
        items_container.add_widget(integrations_item)
        
        system_item = SettingsItem(
            title='System Info',
            subtitle='Firmware, Storage',
            on_press=lambda x: self.goto('system')
        )
        items_container.add_widget(system_item)
        
        scroll.add_widget(items_container)
        layout.add_widget(scroll)
        self.add_widget(layout)
    
    def on_device_name_pressed(self, instance):
        pass
    
    def on_integrations_pressed(self, instance):
        pass
