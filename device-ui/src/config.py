"""
MeetingBox Device UI Configuration

Configure display, backend connection, and UI preferences.
"""

import os
from pathlib import Path

# ============================================================================
# BACKEND CONNECTION
# ============================================================================

BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')
BACKEND_WS_URL = os.getenv('BACKEND_WS_URL', 'ws://localhost:8000/ws')

# Use mock backend for testing (set MOCK_BACKEND=1)
USE_MOCK_BACKEND = os.getenv('MOCK_BACKEND', '0') == '1'

# API timeout in seconds
API_TIMEOUT = 30

# WebSocket reconnect settings
WS_RECONNECT_DELAY = 3  # seconds
WS_MAX_RECONNECT_ATTEMPTS = 10

# ============================================================================
# DISPLAY SETTINGS
# ============================================================================

# Display resolution
# 3.5" OLED touchscreen in landscape orientation
# Native: 320x480, Landscape: 480x320
DISPLAY_WIDTH = int(os.getenv('DISPLAY_WIDTH', '480'))
DISPLAY_HEIGHT = int(os.getenv('DISPLAY_HEIGHT', '320'))

# Display orientation
# Options: 'portrait', 'landscape'
DISPLAY_ORIENTATION = os.getenv('DISPLAY_ORIENTATION', 'landscape')

# Framerate (FPS)
# Lower FPS saves CPU on Raspberry Pi
# 30 FPS = smooth, 20 FPS = acceptable, 15 FPS = choppy
TARGET_FPS = int(os.getenv('TARGET_FPS', '30'))

# Fullscreen mode
FULLSCREEN = os.getenv('FULLSCREEN', '1') == '1'

# ============================================================================
# TOUCH SETTINGS
# ============================================================================

# Touch device path (auto-detect if None)
TOUCH_DEVICE = os.getenv('TOUCH_DEVICE', None)

# Touch calibration (if needed)
# Format: "x_min x_max y_min y_max"
TOUCH_CALIBRATION = os.getenv('TOUCH_CALIBRATION', None)

# Double-tap time window (milliseconds)
DOUBLE_TAP_TIME = 400

# Long-press duration (milliseconds)
LONG_PRESS_TIME = 1000

# ============================================================================
# UI THEME
# ============================================================================

# Color palette – Apple-inspired premium dark theme (RGBA 0-1)
COLORS = {
    # Primary (blue gradient endpoints)
    'primary_start': (0.22, 0.55, 0.98, 1),    # #3888FA  bright blue
    'primary_end': (0.13, 0.45, 0.96, 1),      # #2273F5  deep blue
    'primary_text': (1, 1, 1, 1),

    # iOS-style status colours
    'green': (0.20, 0.78, 0.35, 1),             # #34C759
    'red': (1.0, 0.27, 0.23, 1),                # #FF453A
    'yellow': (1.0, 0.80, 0.0, 1),              # #FFD60A
    'blue': (0.04, 0.52, 1.0, 1),               # #0A84FF

    # Blue variants (backward compat)
    'blue_50': (0.94, 0.95, 1.0, 1),            # #EFF6FF

    # Surfaces
    'background': (0.11, 0.11, 0.12, 1),        # #1C1C1E  dark bg
    'surface': (0.17, 0.17, 0.18, 1),           # #2C2C2E  elevated
    'surface_light': (0.22, 0.22, 0.23, 1),     # #38383A  card bg

    # Neutrals
    'white': (1, 1, 1, 1),
    'gray_50': (0.98, 0.98, 0.99, 1),
    'gray_100': (0.96, 0.96, 0.97, 1),
    'gray_200': (0.92, 0.92, 0.93, 1),
    'gray_300': (0.78, 0.78, 0.80, 1),          # #C7C7CC
    'gray_400': (0.68, 0.68, 0.70, 1),          # #AEAEB2
    'gray_500': (0.56, 0.56, 0.58, 1),          # #8E8E93
    'gray_600': (0.44, 0.44, 0.46, 1),          # #6E6E73
    'gray_700': (0.33, 0.33, 0.35, 1),          # #545458
    'gray_800': (0.23, 0.23, 0.24, 1),          # #3A3A3C
    'gray_900': (0.11, 0.11, 0.12, 1),          # #1C1C1E
    'black': (0, 0, 0, 1),

    # Shadows
    'shadow': (0, 0, 0, 0.30),
    'shadow_light': (0, 0, 0, 0.15),

    # Transparent
    'transparent': (0, 0, 0, 0),
}

# Premium typography (SF Pro-like sizing)
FONT_SIZES = {
    'huge': 32,
    'large': 22,
    'medium': 17,     # iOS standard body
    'small': 13,
    'tiny': 11,
}

# Button sizes (width, height in pixels)
BUTTON_SIZES = {
    'primary': (180, 60),
    'secondary': (120, 45),
    'small': (100, 40),
}

# Apple-like spacing
SPACING = {
    'screen_padding': 16,
    'button_spacing': 12,
    'section_spacing': 20,
    'list_item_spacing': 8,
}

# More rounded corners (Apple style)
BORDER_RADIUS = 14

# ============================================================================
# ANIMATIONS
# ============================================================================

# Enable animations (disable to save CPU)
ENABLE_ANIMATIONS = True

# Animation durations (seconds)
ANIMATION_DURATION = {
    'fast': 0.15,
    'normal': 0.3,
    'slow': 0.5,
}

# ============================================================================
# FEATURES
# ============================================================================

# Enable live captions during recording
ENABLE_LIVE_CAPTIONS = True

# Live caption update interval (seconds)
LIVE_CAPTION_UPDATE_INTERVAL = 2

# Auto-return to home after processing complete (seconds)
AUTO_RETURN_DELAY = 10

# Number of recent meetings to show in list
MEETINGS_LIST_LIMIT = 20

# Enable haptic feedback (if hardware supports)
ENABLE_HAPTIC = False

# ============================================================================
# LOGGING
# ============================================================================

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Log file path
LOG_FILE = os.getenv('LOG_FILE', '/var/log/meetingbox-ui.log')

# Log to console as well
LOG_TO_CONSOLE = os.getenv('LOG_TO_CONSOLE', '1') == '1'

# ============================================================================
# PATHS
# ============================================================================

# Base directory
BASE_DIR = Path(__file__).parent.parent.resolve()

# Assets directory
ASSETS_DIR = BASE_DIR / 'assets'
FONTS_DIR = ASSETS_DIR / 'fonts'
ICONS_DIR = ASSETS_DIR / 'icons'

# Ensure directories exist
ASSETS_DIR.mkdir(exist_ok=True)
FONTS_DIR.mkdir(exist_ok=True)
ICONS_DIR.mkdir(exist_ok=True)

# ============================================================================
# DEVELOPMENT
# ============================================================================

# Development mode (enables debug features)
DEV_MODE = os.getenv('DEV_MODE', '0') == '1'

# Show FPS counter
SHOW_FPS = DEV_MODE or os.getenv('SHOW_FPS', '0') == '1'

# Enable debug borders on widgets
DEBUG_BORDERS = DEV_MODE and os.getenv('DEBUG_BORDERS', '0') == '1'
