"""
Recording Screen

Landscape layout: Timer + controls left, live captions right.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

from screens.base_screen import BaseScreen
from components.button import SecondaryButton, DangerButton
from components.status_bar import StatusBar
from config import COLORS, FONT_SIZES, SPACING


class RecordingScreen(BaseScreen):
    """
    Recording screen — landscape 480x320.
    
    Left:  Timer, speaker count, pause/stop buttons
    Right: Live caption scroll area
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.elapsed_seconds = 0
        self.timer_event = None
        self.transcript_lines = []
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical')
        
        # Thin status bar
        self.status_bar = StatusBar(
            status_text='RECORDING',
            status_color=COLORS['red'],
            device_name='Conference Room A',
            pulsing=True
        )
        layout.add_widget(self.status_bar)
        
        # Horizontal split
        content = BoxLayout(
            orientation='horizontal',
            padding=SPACING['screen_padding'],
            spacing=SPACING['section_spacing']
        )
        
        # LEFT: Timer + controls
        left = BoxLayout(
            orientation='vertical',
            size_hint=(0.4, 1),
            spacing=SPACING['button_spacing']
        )
        
        self.timer_label = Label(
            text='00:00',
            font_size=FONT_SIZES['huge'],
            size_hint=(1, 0.3),
            color=COLORS['gray_900'],
            bold=True
        )
        left.add_widget(self.timer_label)
        
        self.speaker_label = Label(
            text='0 speakers',
            font_size=FONT_SIZES['tiny'],
            size_hint=(1, 0.1),
            color=COLORS['gray_700']
        )
        left.add_widget(self.speaker_label)
        
        self.pause_btn = SecondaryButton(
            text='PAUSE',
            size_hint=(1, 0.25)
        )
        self.pause_btn.bind(on_press=self.on_pause_pressed)
        left.add_widget(self.pause_btn)
        
        self.stop_btn = DangerButton(
            text='STOP',
            size_hint=(1, 0.3)
        )
        self.stop_btn.bind(on_press=self.on_stop_pressed)
        left.add_widget(self.stop_btn)
        
        content.add_widget(left)
        
        # RIGHT: Live captions
        right = BoxLayout(
            orientation='vertical',
            size_hint=(0.6, 1),
            spacing=2
        )
        
        caption_header = Label(
            text='Live Caption:',
            font_size=FONT_SIZES['tiny'],
            size_hint=(1, None),
            height=14,
            color=COLORS['gray_600'],
            halign='left'
        )
        caption_header.bind(size=caption_header.setter('text_size'))
        right.add_widget(caption_header)
        
        scroll = ScrollView(size_hint=(1, 1))
        self.transcript_label = Label(
            text='Waiting for speech...',
            font_size=FONT_SIZES['small'],
            size_hint_y=None,
            color=COLORS['gray_700'],
            halign='left',
            valign='top'
        )
        self.transcript_label.bind(texture_size=self.transcript_label.setter('size'))
        scroll.add_widget(self.transcript_label)
        right.add_widget(scroll)
        
        content.add_widget(right)
        layout.add_widget(content)
        self.add_widget(layout)
    
    def on_enter(self):
        self.elapsed_seconds = 0
        self.timer_event = Clock.schedule_interval(self.update_timer, 1.0)
        self.transcript_lines = []
        self.transcript_label.text = 'Waiting for speech...'
    
    def on_leave(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
    
    def update_timer(self, dt):
        self.elapsed_seconds += 1
        hours = self.elapsed_seconds // 3600
        minutes = (self.elapsed_seconds % 3600) // 60
        seconds = self.elapsed_seconds % 60
        if hours > 0:
            self.timer_label.text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            self.timer_label.text = f"{minutes:02d}:{seconds:02d}"
    
    def on_pause_pressed(self, instance):
        if self.app.recording_state['paused']:
            self.app.resume_recording()
        else:
            self.app.pause_recording()
    
    def on_paused(self):
        self.pause_btn.text = 'RESUME'
        self.status_bar.status_text = 'PAUSED'
        self.status_bar.status_color = COLORS['yellow']
        if self.timer_event:
            self.timer_event.cancel()
    
    def on_resumed(self):
        self.pause_btn.text = 'PAUSE'
        self.status_bar.status_text = 'RECORDING'
        self.status_bar.status_color = COLORS['red']
        self.timer_event = Clock.schedule_interval(self.update_timer, 1.0)
    
    def on_stop_pressed(self, instance):
        self.app.stop_recording()
    
    def on_transcription_update(self, text: str, speaker_id: str = None):
        if speaker_id:
            line = f"S{speaker_id}: {text}"
        else:
            line = text
        self.transcript_lines.append(line)
        if len(self.transcript_lines) > 10:
            self.transcript_lines = self.transcript_lines[-10:]
        self.transcript_label.text = '\n'.join(self.transcript_lines)
        
        speakers = set()
        for ln in self.transcript_lines:
            if ln.startswith('S') and ':' in ln:
                speakers.add(ln.split(':')[0].strip())
        if speakers:
            self.speaker_label.text = f"{len(speakers)} speaker{'s' if len(speakers) > 1 else ''}"
