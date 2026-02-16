"""
Setup In Progress Screen

Waiting state while user completes web-based setup.
Exit condition: backend sends setup_complete WebSocket event.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.clock import Clock

from screens.base_screen import BaseScreen
from config import COLORS, FONT_SIZES, SETUP_URL


class SetupProgressScreen(BaseScreen):
    """Setup in progress – waiting for web setup completion."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dot_index = 0
        self._dot_event = None
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical')
        self.make_dark_bg(root)

        root.add_widget(Widget(size_hint=(1, 0.25)))

        # Message 1
        msg1 = Label(
            text='Please complete the setup on:',
            font_size=FONT_SIZES['medium'],
            color=COLORS['white'],
            halign='center',
            size_hint=(1, None), height=28,
        )
        msg1.bind(size=msg1.setter('text_size'))
        root.add_widget(msg1)

        # URL
        url_label = Label(
            text=SETUP_URL,
            font_size=FONT_SIZES['large'],
            bold=True,
            color=COLORS['blue'],
            halign='center',
            size_hint=(1, None), height=32,
        )
        url_label.bind(size=url_label.setter('text_size'))
        root.add_widget(url_label)

        root.add_widget(Widget(size_hint=(1, 0.15)))

        # Pulsing dots
        self.dots_label = Label(
            text='●  ○  ○',
            font_size=FONT_SIZES['large'],
            color=COLORS['gray_500'],
            halign='center',
            size_hint=(1, None), height=30,
        )
        root.add_widget(self.dots_label)

        root.add_widget(Widget(size_hint=(1, 0.35)))
        self.add_widget(root)

    # ------------------------------------------------------------------
    def on_enter(self):
        self._dot_index = 0
        self._dot_event = Clock.schedule_interval(self._animate_dots, 0.5)

    def on_leave(self):
        if self._dot_event:
            self._dot_event.cancel()
            self._dot_event = None

    def _animate_dots(self, _dt):
        self._dot_index = (self._dot_index + 1) % 3
        dots = ['○', '○', '○']
        dots[self._dot_index] = '●'
        self.dots_label.text = '  '.join(dots)

    # Called from main app when setup_complete event arrives
    def on_setup_complete(self, data=None):
        self.goto('all_set', transition='fade')
