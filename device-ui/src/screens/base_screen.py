"""
Base Screen Class

All screens inherit from this to get common functionality.
"""

from kivy.uix.screenmanager import Screen
from kivy.app import App


class BaseScreen(Screen):
    """
    Base class for all screens.
    
    Provides:
    - Access to app instance
    - Access to backend client
    - Common navigation methods
    - Lifecycle hooks
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    @property
    def app(self):
        """Get the main app instance"""
        return App.get_running_app()
    
    @property
    def backend(self):
        """Get backend client"""
        return self.app.backend
    
    def goto(self, screen_name: str):
        """Navigate to another screen"""
        self.app.goto_screen(screen_name)
    
    def go_back(self):
        """Go back to previous screen"""
        self.app.go_back()
    
    # Lifecycle hooks (override in subclasses)
    def on_enter(self):
        """Called when screen becomes active"""
        pass
    
    def on_leave(self):
        """Called when leaving this screen"""
        pass
