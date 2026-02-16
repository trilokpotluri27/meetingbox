"""
You're All Set Screen

Confirmation after successful setup.
Duration: 3 seconds (auto-advance) or tap to skip.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.animation import Animation
from kivy.clock import Clock

from screens.base_screen import BaseScreen
from config import COLORS, FONT_SIZES, ALL_SET_DURATION


class AllSetScreen(BaseScreen):
    """You're All Set – post-setup success screen."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._auto_event = None
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical')
        self.make_dark_bg(root)

        root.add_widget(Widget(size_hint=(1, 0.25)))

        # Green checkmark
        self.check_label = Label(
            text='✓',
            font_size=60,
            bold=True,
            color=COLORS['green'],
            halign='center',
            size_hint=(1, None), height=80,
            opacity=0,
        )
        root.add_widget(self.check_label)

        # Message
        self.msg_label = Label(
            text="You're All Set!",
            font_size=24,
            bold=True,
            color=COLORS['white'],
            halign='center',
            size_hint=(1, None), height=40,
            opacity=0,
        )
        root.add_widget(self.msg_label)

        root.add_widget(Widget(size_hint=(1, 0.4)))
        self.add_widget(root)

    # ------------------------------------------------------------------
    def on_enter(self):
        # Checkmark spring-in
        self.check_label.opacity = 0
        self.msg_label.opacity = 0

        anim_check = Animation(opacity=1, duration=0.5)
        anim_check.start(self.check_label)

        # Text fades in after checkmark
        anim_msg = Animation(opacity=0, duration=0.3) + Animation(opacity=1, duration=0.3)
        anim_msg.start(self.msg_label)

        # Auto-advance
        self._auto_event = Clock.schedule_once(self._go_home, ALL_SET_DURATION)

    def on_leave(self):
        if self._auto_event:
            self._auto_event.cancel()
            self._auto_event = None

    def on_touch_down(self, touch):
        # Tap anywhere to skip
        self._go_home(0)
        return True

    def _go_home(self, _dt):
        if self._auto_event:
            self._auto_event.cancel()
            self._auto_event = None
        self.goto('home', transition='fade')
