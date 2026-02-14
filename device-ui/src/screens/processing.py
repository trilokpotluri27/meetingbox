"""
Processing Screen

Landscape layout: compact progress display.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar

from screens.base_screen import BaseScreen
from components.button import SecondaryButton
from components.status_bar import StatusBar
from config import COLORS, FONT_SIZES, SPACING


class ProcessingScreen(BaseScreen):
    """Processing screen — landscape 480x320."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical')
        
        self.status_bar = StatusBar(
            status_text='PROCESSING',
            status_color=COLORS['yellow'],
            device_name='Conference Room A'
        )
        layout.add_widget(self.status_bar)
        
        # Horizontal: info left, dashboard btn right
        content = BoxLayout(
            orientation='horizontal',
            padding=SPACING['screen_padding'],
            spacing=SPACING['section_spacing']
        )
        
        # Left: progress info
        left = BoxLayout(
            orientation='vertical',
            size_hint=(0.65, 1),
            spacing=SPACING['button_spacing']
        )
        
        self.status_label = Label(
            text='Generating transcript...',
            font_size=FONT_SIZES['large'],
            size_hint=(1, 0.25),
            color=COLORS['gray_900'],
            halign='left'
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        left.add_widget(self.status_label)
        
        self.progress_bar = ProgressBar(max=100, value=0, size_hint=(1, 0.08))
        left.add_widget(self.progress_bar)
        
        self.progress_label = Label(
            text='0%',
            font_size=FONT_SIZES['medium'],
            size_hint=(1, 0.15),
            color=COLORS['gray_700']
        )
        left.add_widget(self.progress_label)
        
        self.meeting_info = Label(
            text='Meeting: Untitled\nDuration: 0 min',
            font_size=FONT_SIZES['small'],
            size_hint=(1, 0.25),
            color=COLORS['gray_700'],
            halign='left'
        )
        self.meeting_info.bind(size=self.meeting_info.setter('text_size'))
        left.add_widget(self.meeting_info)
        
        self.time_estimate = Label(
            text='This may take 2-3 minutes',
            font_size=FONT_SIZES['tiny'],
            size_hint=(1, 0.15),
            color=COLORS['gray_500'],
            halign='left'
        )
        self.time_estimate.bind(size=self.time_estimate.setter('text_size'))
        left.add_widget(self.time_estimate)
        
        content.add_widget(left)
        
        # Right: dashboard button
        right = BoxLayout(
            orientation='vertical',
            size_hint=(0.35, 1),
            spacing=SPACING['button_spacing']
        )
        right.add_widget(Label(size_hint=(1, 0.6)))  # spacer
        
        dashboard_btn = SecondaryButton(
            text='VIEW ON\nDASHBOARD',
            size_hint=(1, 0.4)
        )
        dashboard_btn.bind(on_press=self.on_dashboard_pressed)
        right.add_widget(dashboard_btn)
        
        content.add_widget(right)
        layout.add_widget(content)
        self.add_widget(layout)
    
    def on_processing_started(self, data):
        title = data.get('title', 'Untitled')
        dur = data.get('duration', 0) // 60
        self.meeting_info.text = f"Meeting: {title}\nDuration: {dur} min"
    
    def on_progress_update(self, progress: int, status: str):
        self.progress_bar.value = progress
        self.progress_label.text = f"{progress}%"
        self.status_label.text = status
    
    def on_dashboard_pressed(self, instance):
        pass
