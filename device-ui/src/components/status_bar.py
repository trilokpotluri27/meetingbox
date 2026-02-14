"""
Status Bar Component – Premium Dark Theme

Top bar showing device status with subtle bottom separator.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, Line
from kivy.animation import Animation
from config import COLORS, FONT_SIZES


class StatusBar(BoxLayout):
    """
    Status bar widget (dark themed).

    Shows:
    - Coloured status dot + text (e.g. ● READY)
    - Device / room name on the right
    - Subtle bottom separator line
    """

    def __init__(self, status_text='READY', status_color=None,
                 device_name='MeetingBox', pulsing=False,
                 back_button=False, on_back=None, **kwargs):

        kwargs.setdefault('size_hint', (1, None))
        kwargs.setdefault('height', 44)
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('padding', [16, 8])
        kwargs.setdefault('spacing', 8)

        super().__init__(**kwargs)

        self._status_color = status_color or COLORS['green']
        self.pulsing = pulsing

        # Dark background
        with self.canvas.before:
            Color(*COLORS['background'])
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)

        # Bottom separator
        with self.canvas.after:
            Color(*COLORS['gray_800'])
            self.border_line = Line(
                points=[self.x, self.y, self.x + self.width, self.y],
                width=1,
            )

        self.bind(pos=self._update_bg, size=self._update_bg)

        # --- left: dot + status text ---
        status_container = BoxLayout(
            orientation='horizontal',
            size_hint=(0.5, 1),
            spacing=8,
        )

        self.status_dot = Label(
            text='●',
            font_size=FONT_SIZES['small'],
            color=self._status_color,
            size_hint=(None, 1),
            width=20,
        )
        status_container.add_widget(self.status_dot)

        self.status_label = Label(
            text=status_text,
            font_size=FONT_SIZES['medium'],
            color=COLORS['white'],
            bold=True,
            halign='left',
            size_hint=(1, 1),
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        status_container.add_widget(self.status_label)

        self.add_widget(status_container)

        # --- right: device name ---
        self.device_label = Label(
            text=device_name,
            font_size=FONT_SIZES['small'],
            color=COLORS['gray_400'],
            halign='right',
            size_hint=(0.5, 1),
        )
        self.device_label.bind(size=self.device_label.setter('text_size'))
        self.add_widget(self.device_label)

        if self.pulsing:
            self.start_pulse()

    # -- internal helpers ---------------------------------------------------

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border_line.points = [
            self.x, self.y,
            self.x + self.width, self.y,
        ]

    def start_pulse(self):
        anim = Animation(opacity=0.3, duration=0.8) + Animation(opacity=1, duration=0.8)
        anim.repeat = True
        anim.start(self.status_dot)

    # -- public properties --------------------------------------------------

    @property
    def status_text(self):
        return self.status_label.text

    @status_text.setter
    def status_text(self, value):
        self.status_label.text = value

    @property
    def status_color(self):
        return self._status_color

    @status_color.setter
    def status_color(self, value):
        self._status_color = value
        if hasattr(self, 'status_dot'):
            self.status_dot.color = value
