"""
Sotto - macOS Application Bundle Setup
Build with: python setup_app.py py2app
"""

from setuptools import setup

APP = ['sotto/main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'CFBundleName': 'Sotto',
        'CFBundleDisplayName': 'Sotto',
        'CFBundleIdentifier': 'com.sotto.voicecontrol',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'LSUIElement': True,  # Hide from dock (menubar app)
        'NSMicrophoneUsageDescription': 'Sotto needs microphone access for voice control.',
        'NSAppleEventsUsageDescription': 'Sotto needs automation access to control apps.',
    },
    'packages': ['sotto', 'sotto.core', 'sotto.commands', 'sotto.ui'],
    'includes': [
        'pynput',
        'sounddevice',
        'numpy',
        'faster_whisper',
        'rumps',
        'pydantic',
        'pydantic_settings',
        'yaml',
    ],
    'excludes': ['tkinter'],  # Not needed with notification overlay
    'iconfile': None,  # Add icon path here if available
}

setup(
    app=APP,
    name='Sotto',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
