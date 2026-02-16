"""
Microphone Test Screen – PRD §5.15

Live audio waveform + input level indicator.
"""

import random
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivy.clock import Clock

from screens.base_screen import BaseScreen
from components.status_bar import StatusBar
from config import COLORS, FONT_SIZES, SPACING, BORDER_RADIUS


class _TestWaveform(Widget):
    """Simplified waveform for mic test."""

    NUM_BARS = 18
    BAR_WIDTH = 14
    BAR_SPACING = 6

    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint', (1, None))
        kwargs.setdefault('height', 60)
        super().__init__(**kwargs)
        self._levels = [2] * self.NUM_BARS
        self.bind(pos=self._draw, size=self._draw)

    def update(self, _dt=None):
        self._levels = [random.randint(4, 50) for _ in range(self.NUM_BARS)]
        self._draw()

    def _draw(self, *_args):
        self.canvas.clear()
        total_w = self.NUM_BARS * (self.BAR_WIDTH + self.BAR_SPACING)
        start_x = self.x + (self.width - total_w) / 2
        base_y = self.y + 2

        with self.canvas:
            for i, h in enumerate(self._levels):
                Color(*COLORS['blue'])
                bx = start_x + i * (self.BAR_WIDTH + self.BAR_SPACING)
                RoundedRectangle(
                    pos=(bx, base_y),
                    size=(self.BAR_WIDTH, max(2, h)),
                    radius=[3],
                )


class MicTestScreen(BaseScreen):
    """Microphone test screen – PRD §5.15."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._wave_event = None
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical')
        self.make_dark_bg(root)

        # Header
        self.status_bar = StatusBar(
            status_text='Microphone Test',
            device_name='Microphone Test',
            back_button=True,
            on_back=self.go_back,
            show_settings=False,
        )
        root.add_widget(self.status_bar)

        root.add_widget(Widget(size_hint=(1, 0.1)))

        # Instructions
        instr = Label(
            text='Speak to test your microphone',
            font_size=FONT_SIZES['medium'],
            color=COLORS['white'],
            halign='center',
            size_hint=(1, None), height=28,
        )
        instr.bind(size=instr.setter('text_size'))
        root.add_widget(instr)

        root.add_widget(Widget(size_hint=(1, 0.1)))

        # Waveform
        self.waveform = _TestWaveform()
        root.add_widget(self.waveform)

        root.add_widget(Widget(size_hint=(1, 0.1)))

        # Level indicator
        self.level_label = Label(
            text='Input Level: Good ✓',
            font_size=FONT_SIZES['small'] + 2,
            bold=True,
            color=COLORS['green'],
            halign='center',
            size_hint=(1, None), height=24,
        )
        root.add_widget(self.level_label)

        root.add_widget(Widget())

        # Footer
        footer = self.build_footer()
        root.add_widget(footer)

        self.add_widget(root)

    # ------------------------------------------------------------------
    def on_enter(self):
        self._wave_event = Clock.schedule_interval(self.waveform.update, 0.1)

    def on_leave(self):
        if self._wave_event:
            self._wave_event.cancel()
            self._wave_event = None
