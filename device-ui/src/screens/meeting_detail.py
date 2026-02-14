"""
Meeting Detail Screen

Landscape: scrollable compact detail view.
"""

from datetime import datetime
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from async_helper import run_async

from screens.base_screen import BaseScreen
from components.status_bar import StatusBar
from components.button import SecondaryButton, DangerButton
from components.action_item import ActionItemWidget
from config import COLORS, FONT_SIZES, SPACING


class MeetingDetailScreen(BaseScreen):
    """Meeting detail — landscape 480x320."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.meeting_id = None
        self.meeting = None
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical')
        
        self.status_bar = StatusBar(
            status_text='<- BACK',
            device_name='Meeting Detail',
            back_button=True,
            on_back=self.go_back
        )
        layout.add_widget(self.status_bar)
        
        # Scrollable content
        scroll = ScrollView()
        self.content = BoxLayout(
            orientation='vertical',
            spacing=SPACING['section_spacing'],
            size_hint_y=None,
            padding=SPACING['screen_padding']
        )
        self.content.bind(minimum_height=self.content.setter('height'))
        
        # Title
        self.title_label = Label(
            text='Loading...',
            font_size=FONT_SIZES['large'],
            size_hint_y=None, height=24,
            color=COLORS['gray_900'],
            bold=True, halign='left', valign='top'
        )
        self.title_label.bind(size=self.title_label.setter('text_size'))
        self.content.add_widget(self.title_label)
        
        # Metadata
        self.meta_label = Label(
            text='',
            font_size=FONT_SIZES['tiny'],
            size_hint_y=None, height=16,
            color=COLORS['gray_600'], halign='left'
        )
        self.meta_label.bind(size=self.meta_label.setter('text_size'))
        self.content.add_widget(self.meta_label)
        
        # Summary
        self.summary_container = BoxLayout(
            orientation='vertical', size_hint_y=None,
            spacing=SPACING['button_spacing']
        )
        self.content.add_widget(self.summary_container)
        
        # Action items
        self.actions_container = BoxLayout(
            orientation='vertical', size_hint_y=None,
            spacing=SPACING['button_spacing']
        )
        self.content.add_widget(self.actions_container)
        
        # Decisions
        self.decisions_container = BoxLayout(
            orientation='vertical', size_hint_y=None,
            spacing=SPACING['button_spacing']
        )
        self.content.add_widget(self.decisions_container)
        
        # Action buttons
        buttons = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=36,
            spacing=SPACING['button_spacing']
        )
        dashboard_btn = SecondaryButton(text='DASHBOARD')
        dashboard_btn.bind(on_press=self.on_dashboard_pressed)
        buttons.add_widget(dashboard_btn)
        
        delete_btn = DangerButton(text='DELETE')
        delete_btn.bind(on_press=self.on_delete_pressed)
        buttons.add_widget(delete_btn)
        self.content.add_widget(buttons)
        
        scroll.add_widget(self.content)
        layout.add_widget(scroll)
        self.add_widget(layout)
    
    def set_meeting_id(self, meeting_id: str):
        self.meeting_id = meeting_id
    
    def on_enter(self):
        if self.meeting_id:
            self.load_meeting()
    
    def load_meeting(self):
        async def _load():
            try:
                meeting = await self.backend.get_meeting_detail(self.meeting_id)
                self.meeting = meeting
                Clock.schedule_once(lambda dt: self.populate_meeting(), 0)
            except Exception as e:
                print(f"Failed to load meeting: {e}")
                Clock.schedule_once(lambda dt: self.go_back(), 0)
        run_async(_load())
    
    def populate_meeting(self):
        if not self.meeting:
            return
        self.title_label.text = self.meeting['title']
        start_time = datetime.fromisoformat(self.meeting['start_time'].replace('Z', '+00:00'))
        dur = self.meeting.get('duration', 0) // 60
        self.meta_label.text = f"{start_time.strftime('%b %d, %I:%M %p')} - {dur}min"
        
        summary = self.meeting.get('summary', {})
        self.populate_summary(summary)
        self.populate_action_items(summary.get('action_items', []))
        self.populate_decisions(summary.get('decisions', []))
    
    def populate_summary(self, summary: dict):
        self.summary_container.clear_widgets()
        header = Label(
            text='Summary', font_size=FONT_SIZES['medium'],
            size_hint_y=None, height=18,
            color=COLORS['gray_900'], bold=True, halign='left'
        )
        header.bind(size=header.setter('text_size'))
        self.summary_container.add_widget(header)
        
        text_label = Label(
            text=summary.get('summary', 'No summary'),
            font_size=FONT_SIZES['small'],
            size_hint_y=None, color=COLORS['gray_700'],
            halign='left', valign='top'
        )
        text_label.bind(texture_size=text_label.setter('size'))
        text_label.bind(size=text_label.setter('text_size'))
        self.summary_container.add_widget(text_label)
        self.summary_container.height = 18 + text_label.height + SPACING['button_spacing']
    
    def populate_action_items(self, items: list):
        self.actions_container.clear_widgets()
        if not items:
            return
        header = Label(
            text=f'Actions ({len(items)})', font_size=FONT_SIZES['medium'],
            size_hint_y=None, height=18,
            color=COLORS['gray_900'], bold=True, halign='left'
        )
        header.bind(size=header.setter('text_size'))
        self.actions_container.add_widget(header)
        total = 18
        for item in items:
            w = ActionItemWidget(action_item=item)
            self.actions_container.add_widget(w)
            total += w.height + SPACING['button_spacing']
        self.actions_container.height = total
    
    def populate_decisions(self, decisions: list):
        self.decisions_container.clear_widgets()
        if not decisions:
            return
        header = Label(
            text=f'Decisions ({len(decisions)})', font_size=FONT_SIZES['medium'],
            size_hint_y=None, height=18,
            color=COLORS['gray_900'], bold=True, halign='left'
        )
        header.bind(size=header.setter('text_size'))
        self.decisions_container.add_widget(header)
        total = 18
        for d in decisions:
            dl = Label(
                text=f'- {d}', font_size=FONT_SIZES['small'],
                size_hint_y=None, color=COLORS['gray_700'],
                halign='left', valign='top'
            )
            dl.bind(texture_size=dl.setter('size'))
            dl.bind(size=dl.setter('text_size'))
            self.decisions_container.add_widget(dl)
            total += dl.height + SPACING['button_spacing']
        self.decisions_container.height = total
    
    def on_dashboard_pressed(self, instance):
        pass
    
    def on_delete_pressed(self, instance):
        async def _delete():
            try:
                await self.backend.delete_meeting(self.meeting_id)
                Clock.schedule_once(lambda dt: self.goto('meetings'), 0)
            except Exception as e:
                print(f"Failed to delete meeting: {e}")
        run_async(_delete())
