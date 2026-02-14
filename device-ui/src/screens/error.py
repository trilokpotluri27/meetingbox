"""
Error Screen

Landscape compact layout.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from screens.base_screen import BaseScreen
from components.button import PrimaryButton
from components.status_bar import StatusBar
from config import COLORS, FONT_SIZES, SPACING


class ErrorScreen(BaseScreen):
    """Error screen — landscape 480x320."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error_type = "Error"
        self.error_message = "An error occurred"
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical')
        
        self.status_bar = StatusBar(
            status_text='ERROR',
            status_color=COLORS['red'],
            device_name='MeetingBox'
        )
        layout.add_widget(self.status_bar)
        
        # Horizontal: error info left, action right
        content = BoxLayout(
            orientation='horizontal',
            padding=SPACING['screen_padding'],
            spacing=SPACING['section_spacing']
        )
        
        # Left: error details
        left = BoxLayout(
            orientation='vertical',
            size_hint=(0.6, 1),
            spacing=SPACING['button_spacing']
        )
        
        icon_label = Label(
            text='!',
            font_size=32,
            size_hint=(1, 0.25),
            color=COLORS['red'],
            bold=True
        )
        left.add_widget(icon_label)
        
        self.type_label = Label(
            text=self.error_type,
            font_size=FONT_SIZES['large'],
            size_hint=(1, 0.25),
            color=COLORS['gray_900'],
            bold=True,
            halign='left'
        )
        self.type_label.bind(size=self.type_label.setter('text_size'))
        left.add_widget(self.type_label)
        
        self.message_label = Label(
            text=self.error_message,
            font_size=FONT_SIZES['small'],
            size_hint=(1, 0.5),
            color=COLORS['gray_700'],
            halign='left',
            valign='top'
        )
        self.message_label.bind(size=self.message_label.setter('text_size'))
        left.add_widget(self.message_label)
        
        content.add_widget(left)
        
        # Right: go home button
        right = BoxLayout(
            orientation='vertical',
            size_hint=(0.4, 1),
            spacing=SPACING['button_spacing']
        )
        right.add_widget(Label(size_hint=(1, 0.4)))  # spacer
        
        home_btn = PrimaryButton(
            text='GO HOME',
            size_hint=(1, 0.4)
        )
        home_btn.bind(on_press=lambda x: self.goto('home'))
        right.add_widget(home_btn)
        
        right.add_widget(Label(size_hint=(1, 0.2)))  # spacer
        
        content.add_widget(right)
        layout.add_widget(content)
        self.add_widget(layout)
    
    def set_error(self, error_type: str, message: str):
        self.error_type = error_type
        self.error_message = message
        self.type_label.text = error_type
        self.message_label.text = message
