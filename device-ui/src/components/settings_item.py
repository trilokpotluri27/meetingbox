"""
Settings Item Component

Row in settings menu.
"""

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from config import COLORS, FONT_SIZES, SPACING


class SettingsItem(ButtonBehavior, BoxLayout):
    """
    Settings menu item.
    
    Shows:
    - Title
    - Subtitle (current value)
    - Arrow (->)
    """
    
    def __init__(self, title: str, subtitle: str = '', on_press=None, **kwargs):
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', 48)
        kwargs.setdefault('padding', SPACING['button_spacing'])
        kwargs.setdefault('spacing', 4)
        
        super().__init__(**kwargs)
        
        if on_press:
            self.bind(on_press=on_press)
        
        # Background
        with self.canvas.before:
            Color(*COLORS['white'])
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        # Text container
        text_container = BoxLayout(
            orientation='vertical',
            size_hint=(0.9, 1),
            spacing=4
        )
        
        # Title
        title_label = Label(
            text=title,
            font_size=FONT_SIZES['medium'],
            color=COLORS['gray_900'],
            bold=True,
            halign='left',
            valign='bottom',
            size_hint=(1, 0.5)
        )
        title_label.bind(size=title_label.setter('text_size'))
        text_container.add_widget(title_label)
        
        # Subtitle
        subtitle_label = Label(
            text=subtitle,
            font_size=FONT_SIZES['small'],
            color=COLORS['gray_600'],
            halign='left',
            valign='top',
            size_hint=(1, 0.5)
        )
        subtitle_label.bind(size=subtitle_label.setter('text_size'))
        text_container.add_widget(subtitle_label)
        
        self.add_widget(text_container)
        
        # Arrow
        arrow = Label(
            text='>',
            font_size=FONT_SIZES['large'],
            color=COLORS['gray_400'],
            size_hint=(0.1, 1)
        )
        self.add_widget(arrow)
        
        # Bottom border
        with self.canvas.after:
            Color(*COLORS['gray_200'])
            self.border = Rectangle(
                pos=(self.x, self.y),
                size=(self.width, 1)
            )
        
        self.bind(pos=self._update_border, size=self._update_border)
    
    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
    
    def _update_border(self, *args):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(*COLORS['gray_200'])
            self.border = Rectangle(
                pos=(self.x, self.y),
                size=(self.width, 1)
            )
    
    def on_press(self):
        """Darken on press"""
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*COLORS['gray_100'])
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
    
    def on_release(self):
        """Restore on release"""
        self._update_bg()
