"""
MeetingBox Device UI - Main Application

Entry point for the OLED touchscreen interface.
"""

import asyncio
import logging
import sys
from pathlib import Path

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.config import Config

# Configure Kivy before importing other modules
Config.set('graphics', 'window_state', 'visible')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

# Import config
from config import (
    DISPLAY_WIDTH,
    DISPLAY_HEIGHT,
    FULLSCREEN,
    TARGET_FPS,
    USE_MOCK_BACKEND,
    LOG_LEVEL,
    LOG_FILE,
    LOG_TO_CONSOLE,
    SHOW_FPS
)

# Import API client
from api_client import BackendClient
from mock_backend import MockBackendClient

# Import screens (will be created in Part 3)
from screens.setup import SetupScreen
from screens.home import HomeScreen
from screens.recording import RecordingScreen
from screens.processing import ProcessingScreen
from screens.complete import CompleteScreen
from screens.meetings import MeetingsScreen
from screens.meeting_detail import MeetingDetailScreen
from screens.settings import SettingsScreen
from screens.wifi import WiFiScreen
from screens.system import SystemScreen
from screens.error import ErrorScreen

# Setup logging
def setup_logging():
    """Configure logging for the application"""
    handlers = []
    
    # Console handler
    if LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        handlers.append(console_handler)
    
    # File handler
    try:
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        handlers.append(file_handler)
    except Exception as e:
        print(f"Warning: Could not create log file {LOG_FILE}: {e}")
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        handlers=handlers
    )

setup_logging()
logger = logging.getLogger(__name__)

# Import async helper (starts background event loop on import)
from async_helper import run_async, get_async_loop


class MeetingBoxApp(App):
    """
    Main Kivy application for MeetingBox OLED UI.
    
    Manages:
    - Screen navigation
    - Backend API connection
    - Real-time event handling
    - Application state
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
            'live_caption': ''
        }
        
        # Screen manager
        self.screen_manager = None
        
        # WebSocket task
        self.ws_task = None
        
    def build(self):
        """Build the application UI"""
        logger.info("Building MeetingBox UI")
        
        # Set window size
        Window.size = (DISPLAY_WIDTH, DISPLAY_HEIGHT)
        
        # Set fullscreen if configured
        if FULLSCREEN:
            Window.fullscreen = 'auto'
        
        # Show FPS if configured
        if SHOW_FPS:
            Window.show_cursor = True
        else:
            Window.show_cursor = False
        
        # Create screen manager with no transition (instant switching)
        self.screen_manager = ScreenManager(transition=NoTransition())
        
        # Add all screens
        self.screen_manager.add_widget(SetupScreen(name='setup'))
        self.screen_manager.add_widget(HomeScreen(name='home'))
        self.screen_manager.add_widget(RecordingScreen(name='recording'))
        self.screen_manager.add_widget(ProcessingScreen(name='processing'))
        self.screen_manager.add_widget(CompleteScreen(name='complete'))
        self.screen_manager.add_widget(MeetingsScreen(name='meetings'))
        self.screen_manager.add_widget(MeetingDetailScreen(name='meeting_detail'))
        self.screen_manager.add_widget(SettingsScreen(name='settings'))
        self.screen_manager.add_widget(WiFiScreen(name='wifi'))
        self.screen_manager.add_widget(SystemScreen(name='system'))
        self.screen_manager.add_widget(ErrorScreen(name='error'))
        
        # Check if setup is needed
        if self.needs_setup():
            self.screen_manager.current = 'setup'
        else:
            self.screen_manager.current = 'home'
        
        # Start WebSocket listener
        self.start_websocket_listener()
        
        # Schedule FPS display if enabled
        if SHOW_FPS:
            Clock.schedule_interval(self.update_fps, 1.0)
        
        logger.info(f"UI built, starting on screen: {self.screen_manager.current}")
        return self.screen_manager
    
    def needs_setup(self) -> bool:
        """
        Check if initial setup is required.
        
        Returns:
            True if setup needed, False otherwise
        """
        # Skip setup check when using mock backend (dev/testing mode)
        if USE_MOCK_BACKEND:
            return False
        
        # Check for setup completion marker file
        setup_marker = Path('/opt/meetingbox/.setup_complete')
        return not setup_marker.exists()
    
    def on_start(self):
        """Called when application starts"""
        logger.info("MeetingBox UI started")
        
        # Check backend health
        Clock.schedule_once(self.check_backend_health, 1.0)
    
    def on_stop(self):
        """Called when application stops"""
        logger.info("MeetingBox UI stopping")
        
        # Cancel WebSocket task
        if self.ws_task and not self.ws_task.done():
            self.ws_task.cancel()
        
        # Close backend client
        run_async(self.backend.close())
    
    # ========================================================================
    # BACKEND HEALTH
    # ========================================================================
    
    def check_backend_health(self, dt):
        """Check if backend is reachable"""
        async def _check():
            healthy = await self.backend.health_check()
            if not healthy:
                logger.error("Backend health check failed")
                Clock.schedule_once(
                    lambda dt: self.show_error_screen("Backend Not Available",
                                                     "Cannot connect to MeetingBox backend service."),
                    0
                )
        
        run_async(_check())
    
    # ========================================================================
    # WEBSOCKET EVENT HANDLING
    # ========================================================================
    
    def start_websocket_listener(self):
        """Start listening to backend WebSocket events"""
        loop = get_async_loop()
        if loop and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._websocket_listener(), loop)
            self.ws_task = future
    
    async def _websocket_listener(self):
        """Listen for WebSocket events and dispatch to handlers"""
        try:
            async for event in self.backend.subscribe_events():
                event_type = event.get('type')
                data = event.get('data', {})
                
                logger.debug(f"WebSocket event: {event_type}")
                
                # Dispatch to appropriate handler
                if event_type == 'recording_started':
                    self.on_recording_started(data)
                elif event_type == 'recording_stopped':
                    self.on_recording_stopped(data)
                elif event_type == 'recording_paused':
                    self.on_recording_paused(data)
                elif event_type == 'recording_resumed':
                    self.on_recording_resumed(data)
                elif event_type == 'transcription_update':
                    self.on_transcription_update(data)
                elif event_type == 'processing_started':
                    self.on_processing_started(data)
                elif event_type == 'processing_progress':
                    self.on_processing_progress(data)
                elif event_type == 'processing_complete':
                    self.on_processing_complete(data)
                elif event_type == 'error':
                    self.on_error_event(data)
                elif event_type == 'heartbeat':
                    pass  # Ignore heartbeats
                else:
                    logger.warning(f"Unknown event type: {event_type}")
        
        except asyncio.CancelledError:
            logger.info("WebSocket listener cancelled")
        except Exception as e:
            logger.error(f"WebSocket listener error: {e}")
            # Try to reconnect
            await asyncio.sleep(5)
            Clock.schedule_once(lambda dt: self.start_websocket_listener(), 0)
    
    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================
    
    def on_recording_started(self, data):
        """Handle recording started event"""
        self.current_session_id = data.get('session_id')
        self.recording_state['active'] = True
        self.recording_state['paused'] = False
        self.recording_state['elapsed'] = 0
        
        # Switch to recording screen
        Clock.schedule_once(lambda dt: self.goto_screen('recording'), 0)
    
    def on_recording_stopped(self, data):
        """Handle recording stopped event"""
        self.recording_state['active'] = False
        
        # Switch to processing screen
        Clock.schedule_once(lambda dt: self.goto_screen('processing'), 0)
    
    def on_recording_paused(self, data):
        """Handle recording paused event"""
        self.recording_state['paused'] = True
        
        # Update recording screen
        screen = self.screen_manager.get_screen('recording')
        if hasattr(screen, 'on_paused'):
            Clock.schedule_once(lambda dt: screen.on_paused(), 0)
    
    def on_recording_resumed(self, data):
        """Handle recording resumed event"""
        self.recording_state['paused'] = False
        
        # Update recording screen
        screen = self.screen_manager.get_screen('recording')
        if hasattr(screen, 'on_resumed'):
            Clock.schedule_once(lambda dt: screen.on_resumed(), 0)
    
    def on_transcription_update(self, data):
        """Handle live transcription update"""
        text = data.get('text', '')
        speaker_id = data.get('speaker_id')
        
        self.recording_state['live_caption'] = text
        
        # Update recording screen
        screen = self.screen_manager.get_screen('recording')
        if hasattr(screen, 'on_transcription_update'):
            Clock.schedule_once(
                lambda dt: screen.on_transcription_update(text, speaker_id), 
                0
            )
    
    def on_processing_started(self, data):
        """Handle processing started event"""
        # Already on processing screen, just update
        screen = self.screen_manager.get_screen('processing')
        if hasattr(screen, 'on_processing_started'):
            Clock.schedule_once(lambda dt: screen.on_processing_started(data), 0)
    
    def on_processing_progress(self, data):
        """Handle processing progress update"""
        progress = data.get('progress', 0)
        status = data.get('status', '')
        
        # Update processing screen
        screen = self.screen_manager.get_screen('processing')
        if hasattr(screen, 'on_progress_update'):
            Clock.schedule_once(
                lambda dt: screen.on_progress_update(progress, status), 
                0
            )
    
    def on_processing_complete(self, data):
        """Handle processing complete event"""
        meeting_id = data.get('meeting_id')
        
        # Switch to complete screen
        def _switch(dt):
            screen = self.screen_manager.get_screen('complete')
            if hasattr(screen, 'set_meeting_id'):
                screen.set_meeting_id(meeting_id)
            self.goto_screen('complete')
        
        Clock.schedule_once(_switch, 0)
    
    def on_error_event(self, data):
        """Handle error event from backend"""
        error_type = data.get('error_type', 'Unknown Error')
        message = data.get('message', '')
        
        Clock.schedule_once(
            lambda dt: self.show_error_screen(error_type, message), 
            0
        )
    
    # ========================================================================
    # NAVIGATION
    # ========================================================================
    
    def goto_screen(self, screen_name: str):
        """
        Navigate to a screen.
        
        Args:
            screen_name: Name of the screen to navigate to
        """
        logger.info(f"Navigating to screen: {screen_name}")
        
        # Call on_leave for current screen
        current = self.screen_manager.current_screen
        if hasattr(current, 'on_leave'):
            current.on_leave()
        
        # Switch screen
        self.screen_manager.current = screen_name
        
        # Call on_enter for new screen
        new_screen = self.screen_manager.current_screen
        if hasattr(new_screen, 'on_enter'):
            new_screen.on_enter()
    
    def go_back(self):
        """Go back to previous screen"""
        # Simple back navigation - go to home
        # Could be enhanced with screen history stack
        self.goto_screen('home')
    
    def show_error_screen(self, error_type: str, message: str):
        """
        Show error screen with message.
        
        Args:
            error_type: Type/title of error
            message: Error message to display
        """
        screen = self.screen_manager.get_screen('error')
        if hasattr(screen, 'set_error'):
            screen.set_error(error_type, message)
        self.goto_screen('error')
    
    # ========================================================================
    # RECORDING ACTIONS
    # ========================================================================
    
    def start_recording(self):
        """Start a new recording"""
        async def _start():
            try:
                result = await self.backend.start_recording()
                self.current_session_id = result['session_id']
                self.recording_state['active'] = True
                self.recording_state['paused'] = False
                self.recording_state['elapsed'] = 0
                
                # Navigate to recording screen
                Clock.schedule_once(lambda dt: self.goto_screen('recording'), 0)
            
            except Exception as e:
                logger.error(f"Failed to start recording: {e}")
                Clock.schedule_once(
                    lambda dt: self.show_error_screen(
                        "Recording Failed", 
                        "Could not start recording. Please try again."
                    ),
                    0
                )
        
        run_async(_start())
    
    def stop_recording(self):
        """Stop the current recording"""
        if not self.current_session_id:
            logger.warning("No active recording to stop")
            return
        
        async def _stop():
            try:
                await self.backend.stop_recording(self.current_session_id)
                self.recording_state['active'] = False
                
                # Navigate to processing screen
                Clock.schedule_once(lambda dt: self.goto_screen('processing'), 0)
            
            except Exception as e:
                logger.error(f"Failed to stop recording: {e}")
                Clock.schedule_once(
                    lambda dt: self.show_error_screen(
                        "Stop Failed", 
                        "Could not stop recording. Please try again."
                    ),
                    0
                )
        
        run_async(_stop())
    
    def pause_recording(self):
        """Pause the current recording"""
        if not self.current_session_id:
            return
        
        async def _pause():
            try:
                await self.backend.pause_recording(self.current_session_id)
                self.recording_state['paused'] = True
            except Exception as e:
                logger.error(f"Failed to pause recording: {e}")
        
        run_async(_pause())
    
    def resume_recording(self):
        """Resume the paused recording"""
        if not self.current_session_id:
            return
        
        async def _resume():
            try:
                await self.backend.resume_recording(self.current_session_id)
                self.recording_state['paused'] = False
            except Exception as e:
                logger.error(f"Failed to resume recording: {e}")
        
        run_async(_resume())
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def update_fps(self, dt):
        """Update FPS counter (if enabled)"""
        fps = Clock.get_fps()
        logger.debug(f"FPS: {fps:.1f}")
    
    def get_app(self):
        """Get app instance (for screens to access)"""
        return self


def main():
    """Main entry point"""
    logger.info("Starting MeetingBox Device UI")
    
    try:
        # Create and run app
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
