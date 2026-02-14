"""
Complete Screen

Landscape layout: summary left, actions right.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from async_helper import run_async

from screens.base_screen import BaseScreen
from components.button import PrimaryButton, SecondaryButton
from components.status_bar import StatusBar
from config import COLORS, FONT_SIZES, SPACING, AUTO_RETURN_DELAY


class CompleteScreen(BaseScreen):
    """Complete screen — landscape 480x320."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.meeting_id = None
        self.auto_return_event = None
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical')
        
        self.status_bar = StatusBar(
            status_text='COMPLETE',
            status_color=COLORS['green'],
            device_name='Conference Room A'
        )
        layout.add_widget(self.status_bar)
        
        # Horizontal split
        content = BoxLayout(
            orientation='horizontal',
            padding=SPACING['screen_padding'],
            spacing=SPACING['section_spacing']
        )
        
        # Left: meeting info
        left = BoxLayout(
            orientation='vertical',
            size_hint=(0.55, 1),
            spacing=SPACING['button_spacing']
        )
        
        success_label = Label(
            text='Meeting Saved',
            font_size=FONT_SIZES['large'],
            size_hint=(1, 0.2),
            color=COLORS['green'],
            halign='left',
            bold=True
        )
        success_label.bind(size=success_label.setter('text_size'))
        left.add_widget(success_label)
        
        self.meeting_title = Label(
            text='Untitled Meeting',
            font_size=FONT_SIZES['medium'],
            size_hint=(1, 0.2),
            color=COLORS['gray_900'],
            bold=True,
            halign='left'
        )
        self.meeting_title.bind(size=self.meeting_title.setter('text_size'))
        left.add_widget(self.meeting_title)
        
        self.stats_label = Label(
            text='- 0 action items\n- 0 decisions',
            font_size=FONT_SIZES['small'],
            size_hint=(1, 0.35),
            color=COLORS['gray_700'],
            halign='left',
            valign='top'
        )
        self.stats_label.bind(size=self.stats_label.setter('text_size'))
        left.add_widget(self.stats_label)
        
        self.countdown_label = Label(
            text=f'Auto-home in {AUTO_RETURN_DELAY}s',
            font_size=FONT_SIZES['tiny'],
            size_hint=(1, 0.1),
            color=COLORS['gray_500']
        )
        left.add_widget(self.countdown_label)
        
        content.add_widget(left)
        
        # Right: action buttons
        right = BoxLayout(
            orientation='vertical',
            size_hint=(0.45, 1),
            spacing=SPACING['button_spacing']
        )
        
        view_btn = SecondaryButton(
            text='VIEW\nSUMMARY',
            size_hint=(1, 0.45)
        )
        view_btn.bind(on_press=self.on_view_summary)
        right.add_widget(view_btn)
        
        new_btn = PrimaryButton(
            text='NEW\nMEETING',
            size_hint=(1, 0.45)
        )
        new_btn.bind(on_press=self.on_start_new)
        right.add_widget(new_btn)
        
        content.add_widget(right)
        layout.add_widget(content)
        self.add_widget(layout)
    
    def set_meeting_id(self, meeting_id: str):
        self.meeting_id = meeting_id
        self.load_meeting_info()
    
    def load_meeting_info(self):
        if not self.meeting_id:
            return
        async def _load():
            try:
                meeting = await self.backend.get_meeting_detail(self.meeting_id)
                Clock.schedule_once(lambda dt: setattr(self.meeting_title, 'text', meeting['title']), 0)
                summary = meeting.get('summary', {})
                ac = len(summary.get('action_items', []))
                dc = len(summary.get('decisions', []))
                stats = f"- {ac} action item{'s' if ac != 1 else ''}\n- {dc} decision{'s' if dc != 1 else ''}"
                Clock.schedule_once(lambda dt: setattr(self.stats_label, 'text', stats), 0)
            except Exception as e:
                print(f"Failed to load meeting info: {e}")
        run_async(_load())
    
    def on_enter(self):
        self.start_auto_return()
    
    def on_leave(self):
        if self.auto_return_event:
            self.auto_return_event.cancel()
            self.auto_return_event = None
    
    def start_auto_return(self):
        self.countdown_seconds = AUTO_RETURN_DELAY
        self.auto_return_event = Clock.schedule_interval(self.update_countdown, 1.0)
    
    def update_countdown(self, dt):
        self.countdown_seconds -= 1
        if self.countdown_seconds <= 0:
            self.goto('home')
            return False
        self.countdown_label.text = f'Auto-home in {self.countdown_seconds}s'
        return True
    
    def on_view_summary(self, instance):
        if self.meeting_id:
            detail_screen = self.manager.get_screen('meeting_detail')
            detail_screen.set_meeting_id(self.meeting_id)
            self.goto('meeting_detail')
    
    def on_start_new(self, instance):
        self.app.start_recording()
