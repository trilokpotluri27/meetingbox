"""
Meetings List Screen

Landscape: scrollable compact list.
"""

from datetime import datetime, timedelta
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from async_helper import run_async

from screens.base_screen import BaseScreen
from components.status_bar import StatusBar
from components.meeting_card import MeetingCard
from config import SPACING, MEETINGS_LIST_LIMIT


class MeetingsScreen(BaseScreen):
    """Meetings list — landscape 480x320."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.meetings = []
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical')
        
        self.status_bar = StatusBar(
            status_text='<- BACK',
            device_name='Recent Meetings',
            back_button=True,
            on_back=self.go_back
        )
        layout.add_widget(self.status_bar)
        
        scroll = ScrollView()
        self.meetings_container = GridLayout(
            cols=1,
            spacing=SPACING['list_item_spacing'],
            size_hint_y=None,
            padding=SPACING['screen_padding']
        )
        self.meetings_container.bind(minimum_height=self.meetings_container.setter('height'))
        scroll.add_widget(self.meetings_container)
        layout.add_widget(scroll)
        self.add_widget(layout)
    
    def on_enter(self):
        self.load_meetings()
    
    def load_meetings(self):
        async def _load():
            try:
                meetings = await self.backend.get_meetings(limit=MEETINGS_LIST_LIMIT)
                self.meetings = meetings
                Clock.schedule_once(lambda dt: self.populate_meetings(), 0)
            except Exception as e:
                print(f"Failed to load meetings: {e}")
        run_async(_load())
    
    def populate_meetings(self):
        self.meetings_container.clear_widgets()
        if not self.meetings:
            from kivy.uix.label import Label
            from config import COLORS, FONT_SIZES
            empty_label = Label(
                text='No meetings yet',
                font_size=FONT_SIZES['medium'],
                color=COLORS['gray_500'],
                halign='center'
            )
            self.meetings_container.add_widget(empty_label)
            return
        for meeting in self.meetings:
            card = MeetingCard(meeting=meeting)
            card.bind(on_press=self.on_meeting_pressed)
            self.meetings_container.add_widget(card)
    
    def on_meeting_pressed(self, instance):
        meeting_id = instance.meeting['id']
        detail_screen = self.manager.get_screen('meeting_detail')
        detail_screen.set_meeting_id(meeting_id)
        self.goto('meeting_detail')
