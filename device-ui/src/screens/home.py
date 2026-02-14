"""
Home Screen – PREMIUM VERTICAL STACK (480 x 320)

Layout (top → bottom, full width):
┌─────────────────────────────────────────────┐
│ ● READY          Conference Room A          │  44 px  (14 %)
├─────────────────────────────────────────────┤
│ Last: Q4 Planning                           │  40 px  (13 %)
│ 2h ago • 45min                              │
├─────────────────────────────────────────────┤
│                                             │
│         START RECORDING  ⏺                 │ 100 px  (31 %)
│                                             │
├─────────────────────────────────────────────┤
│  ┌──────────┐       ┌──────────┐           │  60 px  (19 %)
│  │ MEETINGS │       │ SETTINGS │           │
│  └──────────┘       └──────────┘           │
├─────────────────────────────────────────────┤
│ (spacer)                                    │  56 px  (17 %)
├─────────────────────────────────────────────┤
│ WiFi: ✓  Storage: 454GB free               │  20 px  ( 6 %)
└─────────────────────────────────────────────┘
"""

from datetime import datetime, timedelta
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.clock import Clock
from async_helper import run_async

from screens.base_screen import BaseScreen
from components.button import PrimaryButton, SecondaryButton
from components.status_bar import StatusBar
from config import COLORS, FONT_SIZES, SPACING, BORDER_RADIUS


class HomeScreen(BaseScreen):
    """
    Home / Ready screen – vertical stacked layout, premium dark theme.

    All sections span the full 480 px width; heights are fixed to sum to 320 px.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_meeting = None
        self._build_ui()

    # -----------------------------------------------------------------------
    #  UI construction
    # -----------------------------------------------------------------------

    def _build_ui(self):
        root = BoxLayout(orientation='vertical')

        # Dark background for entire screen
        with root.canvas.before:
            Color(*COLORS['background'])
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda w, v: setattr(self._bg, 'pos', w.pos),
            size=lambda w, v: setattr(self._bg, 'size', w.size),
        )

        # ---- 1. Status bar  (44 px) ----
        self.status_bar = StatusBar(
            status_text='READY',
            status_color=COLORS['green'],
            device_name='Conference Room A',
            size_hint=(1, None),
            height=44,
        )
        root.add_widget(self.status_bar)

        # ---- 2. Last-meeting card  (40 px) ----
        card = BoxLayout(
            orientation='vertical',
            size_hint=(1, None),
            height=40,
            padding=[SPACING['screen_padding'], 4],
        )
        # Card surface background
        with card.canvas.before:
            Color(*COLORS['surface'])
            self._card_bg = RoundedRectangle(
                pos=card.pos, size=card.size,
                radius=[0],  # full-width band, no rounding
            )
        card.bind(
            pos=lambda w, v: setattr(self._card_bg, 'pos', w.pos),
            size=lambda w, v: setattr(self._card_bg, 'size', w.size),
        )

        self.last_meeting_label = Label(
            text='No meetings yet',
            font_size=FONT_SIZES['small'],
            color=COLORS['gray_400'],
            halign='left',
            valign='middle',
        )
        self.last_meeting_label.bind(
            size=self.last_meeting_label.setter('text_size'),
        )
        card.add_widget(self.last_meeting_label)
        root.add_widget(card)

        # ---- 3. START RECORDING button  (100 px) ----
        btn_wrap = BoxLayout(
            orientation='vertical',
            size_hint=(1, None),
            height=100,
            padding=[SPACING['screen_padding'], 8],
        )
        self.start_btn = PrimaryButton(
            text='START RECORDING  ⏺',
            font_size=FONT_SIZES['large'],
        )
        self.start_btn.bind(on_press=self._on_start_recording)
        btn_wrap.add_widget(self.start_btn)
        root.add_widget(btn_wrap)

        # ---- 4. MEETINGS | SETTINGS buttons  (60 px) ----
        nav_row = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=60,
            padding=[SPACING['screen_padding'], 4],
            spacing=SPACING['button_spacing'],
        )

        meetings_btn = SecondaryButton(
            text='MEETINGS',
            font_size=FONT_SIZES['medium'],
        )
        meetings_btn.bind(on_press=lambda _: self.goto('meetings'))
        nav_row.add_widget(meetings_btn)

        settings_btn = SecondaryButton(
            text='SETTINGS',
            font_size=FONT_SIZES['medium'],
        )
        settings_btn.bind(on_press=lambda _: self.goto('settings'))
        nav_row.add_widget(settings_btn)

        root.add_widget(nav_row)

        # ---- 5. Spacer  (~56 px, flexible) ----
        root.add_widget(Widget())

        # ---- 6. Footer status  (20 px) ----
        self.footer_label = Label(
            text='WiFi: ✓  Storage: … GB free',
            font_size=FONT_SIZES['tiny'],
            size_hint=(1, None),
            height=20,
            color=COLORS['gray_500'],
            halign='left',
            valign='middle',
            padding=[SPACING['screen_padding'], 0],
        )
        self.footer_label.bind(
            size=self.footer_label.setter('text_size'),
        )
        root.add_widget(self.footer_label)

        self.add_widget(root)

    # -----------------------------------------------------------------------
    #  Lifecycle
    # -----------------------------------------------------------------------

    def on_enter(self):
        self._load_last_meeting()
        self._load_system_status()

    # -----------------------------------------------------------------------
    #  Actions
    # -----------------------------------------------------------------------

    def _on_start_recording(self, _instance):
        self.app.start_recording()

    # -----------------------------------------------------------------------
    #  Async data loading
    # -----------------------------------------------------------------------

    def _load_last_meeting(self):
        async def _fetch():
            try:
                meetings = await self.backend.get_meetings(limit=1)
                if meetings:
                    m = meetings[0]
                    self.last_meeting = m

                    start = datetime.fromisoformat(
                        m['start_time'].replace('Z', '+00:00')
                    )
                    delta = datetime.now(start.tzinfo) - start

                    if delta < timedelta(hours=1):
                        ago = f"{int(delta.total_seconds() / 60)}m ago"
                    elif delta < timedelta(days=1):
                        ago = f"{int(delta.total_seconds() / 3600)}h ago"
                    else:
                        ago = f"{delta.days}d ago"

                    dur = m['duration'] // 60 if m.get('duration') else 0
                    text = f"Last: {m['title']}\n{ago} • {dur}min"

                    Clock.schedule_once(
                        lambda _dt: setattr(
                            self.last_meeting_label, 'text', text
                        ), 0,
                    )
            except Exception as exc:
                print(f"[HomeScreen] Failed to load last meeting: {exc}")

        run_async(_fetch())

    def _load_system_status(self):
        async def _fetch():
            try:
                info = await self.backend.get_system_info()
                free_gb = (
                    (info['storage_total'] - info['storage_used']) / (1024 ** 3)
                )
                wifi = '✓' if info.get('wifi_ssid') else '✗'
                text = f"WiFi: {wifi}  Storage: {free_gb:.0f}GB free"

                Clock.schedule_once(
                    lambda _dt: setattr(self.footer_label, 'text', text), 0,
                )
            except Exception as exc:
                print(f"[HomeScreen] Failed to load system status: {exc}")

        run_async(_fetch())
