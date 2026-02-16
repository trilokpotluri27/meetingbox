"""
Processing Screen – AI transcription / summary progress (480 × 320)

PRD §5.9 – Centred progress bar, meeting info, time estimate.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.progressbar import ProgressBar
from kivy.graphics import Color, Rectangle, RoundedRectangle

from screens.base_screen import BaseScreen
from components.status_bar import StatusBar
from config import COLORS, FONT_SIZES, SPACING, BORDER_RADIUS


class ProcessingScreen(BaseScreen):
    """Processing screen – PRD §5.9."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical')
        self.make_dark_bg(root)

        # Status bar
        self.status_bar = StatusBar(
            status_text='PROCESSING',
            status_color=COLORS['yellow'],
            device_name='Conference Room A',
            show_settings=True,
        )
        root.add_widget(self.status_bar)

        root.add_widget(Widget(size_hint=(1, 0.08)))

        # Status text
        self.status_label = Label(
            text='Generating transcript and summary…',
            font_size=FONT_SIZES['medium'],
            color=COLORS['white'],
            halign='center',
            size_hint=(1, None), height=28,
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        root.add_widget(self.status_label)

        root.add_widget(Widget(size_hint=(1, None), height=12))

        # Progress bar row
        pb_row = BoxLayout(
            size_hint=(1, None), height=20,
            padding=[40, 0],
        )
        self.progress_bar = ProgressBar(max=100, value=0, size_hint=(1, 1))
        pb_row.add_widget(self.progress_bar)
        root.add_widget(pb_row)

        # Percentage
        self.pct_label = Label(
            text='0%',
            font_size=FONT_SIZES['small'],
            color=COLORS['gray_400'],
            halign='center',
            size_hint=(1, None), height=18,
        )
        root.add_widget(self.pct_label)

        root.add_widget(Widget(size_hint=(1, None), height=12))

        # Meeting info
        self.meeting_label = Label(
            text='Meeting: Untitled\nDuration: 0 minutes',
            font_size=FONT_SIZES['small'] + 2,
            color=COLORS['gray_500'],
            halign='center',
            size_hint=(1, None), height=36,
        )
        self.meeting_label.bind(size=self.meeting_label.setter('text_size'))
        root.add_widget(self.meeting_label)

        # Time estimate
        self.eta_label = Label(
            text='Estimated time remaining: calculating…',
            font_size=FONT_SIZES['small'],
            color=COLORS['gray_500'],
            halign='center',
            size_hint=(1, None), height=20,
        )
        self.eta_label.bind(size=self.eta_label.setter('text_size'))
        root.add_widget(self.eta_label)

        root.add_widget(Widget())

        # Footer
        footer = self.build_footer()
        root.add_widget(footer)

        self.add_widget(root)

    # ------------------------------------------------------------------
    # Backend events
    # ------------------------------------------------------------------
    def on_processing_started(self, data):
        title = data.get('title', 'Untitled')
        dur = data.get('duration', 0) // 60
        self.meeting_label.text = f'Meeting: {title}\nDuration: {dur} minutes'

    def on_progress_update(self, progress: int, status: str):
        self.progress_bar.value = progress
        self.pct_label.text = f'{progress}%'
        if status:
            self.status_label.text = status

        # ETA formatting
        eta = getattr(self, '_eta_seconds', None)
        if eta and eta < 60:
            self.eta_label.text = 'Estimated time remaining: less than 1 minute'
        elif eta:
            self.eta_label.text = f'Estimated time remaining: {eta // 60} minutes'

    def set_eta(self, seconds: int):
        self._eta_seconds = seconds

    # Privacy
    def on_enter(self):
        privacy = getattr(self.app, 'privacy_mode', False)
        if privacy:
            self.status_bar.status_text = 'PROCESSING (Local)'

    def on_dashboard_pressed(self, _inst):
        pass
