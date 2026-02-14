"""
Meeting Card Component

Card showing meeting summary in list.
"""

from datetime import datetime, timedelta
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line
from config import COLORS, FONT_SIZES, BORDER_RADIUS, SPACING


class MeetingCard(ButtonBehavior, BoxLayout):
    """
    Meeting card widget.
    
    Shows:
    - Meeting title
    - Time ago + duration
    - Pending actions (if any)
    """
    
    def __init__(self, meeting: dict, **kwargs):
        self.meeting = meeting
        
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', 52)
        kwargs.setdefault('padding', SPACING['button_spacing'])
        kwargs.setdefault('spacing', 2)
        
        super().__init__(**kwargs)
        
        # Background
        with self.canvas.before:
            Color(*COLORS['white'])
            self.bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[BORDER_RADIUS]
            )
            # Border
            Color(*COLORS['gray_200'])
            self.border = Line(
                rounded_rectangle=(
                    self.x, self.y,
                    self.width, self.height,
                    BORDER_RADIUS
                ),
                width=1
            )
        
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        
        # Title
        title = Label(
            text=meeting['title'],
            font_size=FONT_SIZES['medium'],
            color=COLORS['gray_900'],
            bold=True,
            halign='left',
            valign='top',
            size_hint=(1, 0.4)
        )
        title.bind(size=title.setter('text_size'))
        self.add_widget(title)
        
        # Metadata
        meta_text = self._format_metadata()
        meta = Label(
            text=meta_text,
            font_size=FONT_SIZES['small'],
            color=COLORS['gray_600'],
            halign='left',
            valign='top',
            size_hint=(1, 0.3)
        )
        meta.bind(size=meta.setter('text_size'))
        self.add_widget(meta)
        
        # Pending actions (if any)
        if meeting.get('pending_actions', 0) > 0:
            actions = Label(
                text=f"! {meeting['pending_actions']} pending action{'s' if meeting['pending_actions'] > 1 else ''}",
                font_size=FONT_SIZES['small'],
                color=COLORS['yellow'],
                halign='left',
                valign='top',
                size_hint=(1, 0.3)
            )
            actions.bind(size=actions.setter('text_size'))
            self.add_widget(actions)
    
    def _format_metadata(self) -> str:
        """Format time ago + duration text"""
        # Parse start time
        start_time = datetime.fromisoformat(
            self.meeting['start_time'].replace('Z', '+00:00')
        )
        now = datetime.now(start_time.tzinfo)
        delta = now - start_time
        
        # Format time ago
        if delta < timedelta(hours=1):
            time_ago = f"{int(delta.total_seconds() / 60)} min ago"
        elif delta < timedelta(days=1):
            time_ago = f"{int(delta.total_seconds() / 3600)} hr ago"
        else:
            time_ago = f"{delta.days} days ago"
        
        # Format duration
        duration = self.meeting.get('duration', 0)
        if duration:
            duration_min = duration // 60
            return f"{time_ago} - {duration_min} min"
        else:
            return time_ago
    
    def _update_canvas(self, *args):
        """Update background and border"""
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        
        self.canvas.before.remove(self.border)
        with self.canvas.before:
            Color(*COLORS['gray_200'])
            self.border = Line(
                rounded_rectangle=(
                    self.x, self.y,
                    self.width, self.height,
                    BORDER_RADIUS
                ),
                width=1
            )
    
    def on_press(self):
        """Darken background on press"""
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*COLORS['gray_100'])
            self.bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[BORDER_RADIUS]
            )
    
    def on_release(self):
        """Restore background on release"""
        self._update_canvas()
