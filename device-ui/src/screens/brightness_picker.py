"""
Screen Brightness Picker – PRD §5.13

Options: Low, Medium, High
"""

from screens.picker_base import PickerBaseScreen


class BrightnessPickerScreen(PickerBaseScreen):
    _title = 'Screen Brightness'
    _description = None
    _options = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    _setting_key = 'brightness'
    _default = 'high'
