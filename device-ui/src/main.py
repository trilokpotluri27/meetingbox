"""
MeetingBox Device UI – Main Application

Entry point for the 3.5" OLED touchscreen interface (Raspberry Pi 5).
Implements the complete boot flow defined in the PRD:
  Splash → (first-boot? Welcome → WiFi → SetupProgress → AllSet →) Home
"""

import asyncio
import logging
import sys
from pathlib import Path

from kivy.app import App
from kivy.uix.screenmanager import (
    ScreenManager, FadeTransition, SlideTransition, NoTransition
)
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.config import Config

# Configure Kivy before importing other modules
Config.set('graphics', 'window_state', 'visible')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from config import (
    DISPLAY_WIDTH,
    DISPLAY_HEIGHT,
    FULLSCREEN,
    TARGET_FPS,
    USE_MOCK_BACKEND,
    LOG_LEVEL,
    LOG_FILE,
    LOG_TO_CONSOLE,
    SHOW_FPS,
    TRANSITION_DURATION,
    DEFAULT_PRIVACY_MODE,
)

from api_client import BackendClient
from mock_backend import MockBackendClient

# Boot-flow screens
from screens.splash import SplashScreen
from screens.welcome import WelcomeScreen
from screens.wifi_setup import WiFiSetupScreen
from screens.setup_progress import SetupProgressScreen
from screens.all_set import AllSetScreen

# Core screens
from screens.home import HomeScreen
from screens.recording import RecordingScreen
from screens.processing import ProcessingScreen
from screens.complete import CompleteScreen
from screens.error import ErrorScreen

# Settings & sub-screens
from screens.settings import SettingsScreen
from screens.auto_delete_picker import AutoDeletePickerScreen
from screens.brightness_picker import BrightnessPickerScreen
from screens.timeout_picker import TimeoutPickerScreen
from screens.mic_test import MicTestScreen
from screens.update_check import UpdateCheckScreen
from screens.update_install import UpdateInstallScreen

# Retained screens (still useful)
from screens.meetings import MeetingsScreen
from screens.meeting_detail import MeetingDetailScreen
from screens.wifi import WiFiScreen
from screens.system import SystemScreen

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

def setup_logging():
    handlers = []
    if LOG_TO_CONSOLE:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        handlers.append(ch)
    try:
        fh = logging.FileHandler(LOG_FILE)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        handlers.append(fh)
    except Exception as e:
        print(f"Warning: Could not create log file {LOG_FILE}: {e}")
    logging.basicConfig(level=getattr(logging, LOG_LEVEL), handlers=handlers)

setup_logging()
logger = logging.getLogger(__name__)

# Import async helper (starts background loop on import)
from async_helper import run_async, get_async_loop


# ==================================================================
# Application
# ==================================================================

class MeetingBoxApp(App):
    """
    Main Kivy application for MeetingBox OLED UI.

    Manages:
    - Screen navigation with transitions
    - Navigation history stack
    - Backend API connection + WebSocket events
    - Application state (recording, privacy, etc.)
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Backend client
        if USE_MOCK_BACKEND:
            self.backend = MockBackendClient()
            logger.info("Using MOCK backend")
        else:
            self.backend = BackendClient()
            logger.info("Using REAL backend")

        # Application state
        self.current_session_id = None
        self.recording_state = {
            'active': False,
            'paused': False,
            'elapsed': 0,
            'speaker_count': 0,
            'live_caption': '',
        }
        self.privacy_mode = DEFAULT_PRIVACY_MODE

        # Screen manager & nav stack
        self.screen_manager = None
        self._nav_stack = []

        # WebSocket
        self.ws_task = None

    # ==================================================================
    # BUILD
    # ==================================================================

    def build(self):
        logger.info("Building MeetingBox UI")

        Window.size = (DISPLAY_WIDTH, DISPLAY_HEIGHT)
        if FULLSCREEN:
            Window.fullscreen = 'auto'

        # Hide cursor on production device
        if not SHOW_FPS:
            Window.show_cursor = False

        # Screen manager – default to fade transition
        self.screen_manager = ScreenManager(
            transition=FadeTransition(duration=TRANSITION_DURATION['fade']))

        # Register ALL screens
        self.screen_manager.add_widget(SplashScreen(name='splash'))
        self.screen_manager.add_widget(WelcomeScreen(name='welcome'))
        self.screen_manager.add_widget(WiFiSetupScreen(name='wifi_setup'))
        self.screen_manager.add_widget(SetupProgressScreen(name='setup_progress'))
        self.screen_manager.add_widget(AllSetScreen(name='all_set'))

        self.screen_manager.add_widget(HomeScreen(name='home'))
        self.screen_manager.add_widget(RecordingScreen(name='recording'))
        self.screen_manager.add_widget(ProcessingScreen(name='processing'))
        self.screen_manager.add_widget(CompleteScreen(name='complete'))
        self.screen_manager.add_widget(ErrorScreen(name='error'))

        self.screen_manager.add_widget(SettingsScreen(name='settings'))
        self.screen_manager.add_widget(AutoDeletePickerScreen(name='auto_delete_picker'))
        self.screen_manager.add_widget(BrightnessPickerScreen(name='brightness_picker'))
        self.screen_manager.add_widget(TimeoutPickerScreen(name='timeout_picker'))
        self.screen_manager.add_widget(MicTestScreen(name='mic_test'))
        self.screen_manager.add_widget(UpdateCheckScreen(name='update_check'))
        self.screen_manager.add_widget(UpdateInstallScreen(name='update_install'))

        self.screen_manager.add_widget(MeetingsScreen(name='meetings'))
        self.screen_manager.add_widget(MeetingDetailScreen(name='meeting_detail'))
        self.screen_manager.add_widget(WiFiScreen(name='wifi'))
        self.screen_manager.add_widget(SystemScreen(name='system'))

        # BOOT: always start with splash
        self.screen_manager.current = 'splash'

        # Start WebSocket listener
        self.start_websocket_listener()

        if SHOW_FPS:
            Clock.schedule_interval(self._log_fps, 1.0)

        logger.info("UI built – starting on splash screen")
        return self.screen_manager

    # ==================================================================
    # SETUP CHECK
    # ==================================================================

    def needs_setup(self) -> bool:
        if USE_MOCK_BACKEND:
            return False
        setup_marker = Path('/opt/meetingbox/.setup_complete')
        return not setup_marker.exists()

    # ==================================================================
    # APP LIFECYCLE
    # ==================================================================

    def on_start(self):
        logger.info("MeetingBox UI started")
        Clock.schedule_once(self._check_backend, 2.0)

    def on_stop(self):
        logger.info("MeetingBox UI stopping")
        if self.ws_task and not self.ws_task.done():
            self.ws_task.cancel()
        run_async(self.backend.close())

    def _check_backend(self, _dt):
        async def _health():
            ok = await self.backend.health_check()
            if not ok:
                logger.error("Backend health check failed")
        run_async(_health())

    # ==================================================================
    # NAVIGATION (with history stack & transitions)
    # ==================================================================

    def goto_screen(self, screen_name: str, transition='fade'):
        """Navigate to *screen_name* with the specified transition."""
        logger.info(f"Nav → {screen_name} ({transition})")

        # Push current screen onto stack (avoid duplicates)
        current = self.screen_manager.current
        if not self._nav_stack or self._nav_stack[-1] != current:
            self._nav_stack.append(current)

        # Set transition
        self._set_transition(transition)

        # Notify current screen
        cur_screen = self.screen_manager.current_screen
        if hasattr(cur_screen, 'on_leave'):
            cur_screen.on_leave()

        self.screen_manager.current = screen_name

        # Notify new screen
        new_screen = self.screen_manager.current_screen
        if hasattr(new_screen, 'on_enter'):
            new_screen.on_enter()

    def go_back(self):
        """Pop navigation stack and slide back."""
        if self._nav_stack:
            target = self._nav_stack.pop()
            # Skip non-core screens in stack when going back
            skip = {'splash', 'welcome', 'wifi_setup', 'setup_progress', 'all_set'}
            while target in skip and self._nav_stack:
                target = self._nav_stack.pop()
            self._set_transition('slide_right')
            cur = self.screen_manager.current_screen
            if hasattr(cur, 'on_leave'):
                cur.on_leave()
            self.screen_manager.current = target
            new = self.screen_manager.current_screen
            if hasattr(new, 'on_enter'):
                new.on_enter()
        else:
            self.goto_screen('home', transition='fade')

    def _set_transition(self, kind):
        dur = TRANSITION_DURATION.get('fade', 0.3)
        if kind == 'fade':
            self.screen_manager.transition = FadeTransition(duration=dur)
        elif kind == 'slide_left':
            self.screen_manager.transition = SlideTransition(
                direction='left', duration=dur)
        elif kind == 'slide_right':
            self.screen_manager.transition = SlideTransition(
                direction='right', duration=dur)
        elif kind == 'none':
            self.screen_manager.transition = NoTransition()
        else:
            self.screen_manager.transition = FadeTransition(duration=dur)

    # ==================================================================
    # WEBSOCKET EVENT HANDLING
    # ==================================================================

    def start_websocket_listener(self):
        loop = get_async_loop()
        if loop and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._websocket_listener(), loop)
            self.ws_task = future

    async def _websocket_listener(self):
        try:
            async for event in self.backend.subscribe_events():
                etype = event.get('type')
                data = event.get('data', {})
                logger.debug(f"WS event: {etype}")

                dispatch = {
                    'recording_started': self.on_recording_started,
                    'recording_stopped': self.on_recording_stopped,
                    'recording_paused': self.on_recording_paused,
                    'recording_resumed': self.on_recording_resumed,
                    'transcription_update': self.on_transcription_update,
                    'processing_started': self.on_processing_started,
                    'processing_progress': self.on_processing_progress,
                    'processing_complete': self.on_processing_complete,
                    'setup_complete': self.on_setup_complete,
                    'update_progress': self.on_update_progress,
                    'error': self.on_error_event,
                }
                handler = dispatch.get(etype)
                if handler:
                    handler(data)
                elif etype != 'heartbeat':
                    logger.warning(f"Unknown WS event: {etype}")
        except asyncio.CancelledError:
            logger.info("WebSocket listener cancelled")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await asyncio.sleep(5)
            Clock.schedule_once(lambda _: self.start_websocket_listener(), 0)

    # ==================================================================
    # EVENT HANDLERS
    # ==================================================================

    def on_recording_started(self, data):
        self.current_session_id = data.get('session_id')
        self.recording_state.update(active=True, paused=False, elapsed=0)
        Clock.schedule_once(lambda _: self.goto_screen('recording', 'fade'), 0)

    def on_recording_stopped(self, data):
        self.recording_state['active'] = False
        Clock.schedule_once(lambda _: self.goto_screen('processing', 'fade'), 0)

    def on_recording_paused(self, data):
        self.recording_state['paused'] = True
        screen = self.screen_manager.get_screen('recording')
        if hasattr(screen, 'on_paused'):
            Clock.schedule_once(lambda _: screen.on_paused(), 0)

    def on_recording_resumed(self, data):
        self.recording_state['paused'] = False
        screen = self.screen_manager.get_screen('recording')
        if hasattr(screen, 'on_resumed'):
            Clock.schedule_once(lambda _: screen.on_resumed(), 0)

    def on_transcription_update(self, data):
        text = data.get('text', '')
        speaker = data.get('speaker_id')
        self.recording_state['live_caption'] = text
        screen = self.screen_manager.get_screen('recording')
        if hasattr(screen, 'on_transcription_update'):
            Clock.schedule_once(
                lambda _: screen.on_transcription_update(text, speaker), 0)

    def on_processing_started(self, data):
        screen = self.screen_manager.get_screen('processing')
        if hasattr(screen, 'on_processing_started'):
            Clock.schedule_once(lambda _: screen.on_processing_started(data), 0)

    def on_processing_progress(self, data):
        progress = data.get('progress', 0)
        status = data.get('status', '')
        eta = data.get('eta', 0)
        screen = self.screen_manager.get_screen('processing')
        if hasattr(screen, 'on_progress_update'):
            Clock.schedule_once(
                lambda _: screen.on_progress_update(progress, status), 0)
        if eta and hasattr(screen, 'set_eta'):
            screen.set_eta(eta)

    def on_processing_complete(self, data):
        meeting_id = data.get('meeting_id')

        def _switch(_dt):
            screen = self.screen_manager.get_screen('complete')
            if hasattr(screen, 'set_meeting_id'):
                screen.set_meeting_id(meeting_id)
            self.goto_screen('complete', 'fade')

        Clock.schedule_once(_switch, 0)

    def on_setup_complete(self, data):
        """Handle setup_complete WebSocket event during first-boot."""
        logger.info("Setup complete event received")
        screen = self.screen_manager.get_screen('setup_progress')
        if hasattr(screen, 'on_setup_complete'):
            Clock.schedule_once(lambda _: screen.on_setup_complete(data), 0)

    def on_update_progress(self, data):
        progress = data.get('progress', 0)
        stage = data.get('stage', '')
        eta = data.get('eta', 0)
        screen = self.screen_manager.get_screen('update_install')
        if hasattr(screen, 'on_progress_update'):
            Clock.schedule_once(
                lambda _: screen.on_progress_update(progress, stage, eta), 0)

    def on_error_event(self, data):
        error_type = data.get('error_type', 'Unknown Error')
        message = data.get('message', '')
        Clock.schedule_once(
            lambda _: self.show_error_screen(error_type, message), 0)

    # ==================================================================
    # ERROR DISPLAY
    # ==================================================================

    def show_error_screen(self, error_type: str, message: str,
                          recovery_text=None, recovery_action=None):
        screen = self.screen_manager.get_screen('error')
        if hasattr(screen, 'set_error'):
            screen.set_error(error_type, message, recovery_text, recovery_action)
        self.goto_screen('error', 'fade')

    # ==================================================================
    # RECORDING ACTIONS
    # ==================================================================

    def start_recording(self):
        async def _start():
            try:
                result = await self.backend.start_recording()
                self.current_session_id = result['session_id']
                self.recording_state.update(active=True, paused=False, elapsed=0)
                Clock.schedule_once(
                    lambda _: self.goto_screen('recording', 'fade'), 0)
            except Exception as e:
                logger.error(f"Failed to start recording: {e}")
                Clock.schedule_once(
                    lambda _: self.show_error_screen(
                        'Recording Failed',
                        'Microphone error detected. The microphone may be '
                        'disconnected or in use by another application.',
                        recovery_text='TRY AGAIN',
                        recovery_action=self.start_recording), 0)
        run_async(_start())

    def stop_recording(self):
        if not self.current_session_id:
            return
        async def _stop():
            try:
                await self.backend.stop_recording(self.current_session_id)
                self.recording_state['active'] = False
                Clock.schedule_once(
                    lambda _: self.goto_screen('processing', 'fade'), 0)
            except Exception as e:
                logger.error(f"Failed to stop recording: {e}")
                Clock.schedule_once(
                    lambda _: self.show_error_screen(
                        'Stop Failed', str(e)), 0)
        run_async(_stop())

    def pause_recording(self):
        if not self.current_session_id:
            return
        async def _pause():
            try:
                await self.backend.pause_recording(self.current_session_id)
                self.recording_state['paused'] = True
            except Exception as e:
                logger.error(f"Failed to pause: {e}")
        run_async(_pause())

    def resume_recording(self):
        if not self.current_session_id:
            return
        async def _resume():
            try:
                await self.backend.resume_recording(self.current_session_id)
                self.recording_state['paused'] = False
            except Exception as e:
                logger.error(f"Failed to resume: {e}")
        run_async(_resume())

    # ==================================================================
    # UTILITIES
    # ==================================================================

    def _log_fps(self, _dt):
        logger.debug(f"FPS: {Clock.get_fps():.1f}")


# ==================================================================
# ENTRY POINT
# ==================================================================

def main():
    logger.info("Starting MeetingBox Device UI")
    try:
        app = MeetingBoxApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
