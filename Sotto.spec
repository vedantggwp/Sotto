# -*- mode: python ; coding: utf-8 -*-
"""
Sotto PyInstaller Spec File
Build with: pyinstaller Sotto.spec
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect faster-whisper data files (models, etc.)
datas = []
datas += collect_data_files('faster_whisper')

# Hidden imports - all sotto modules
hiddenimports = [
    'sotto',
    'sotto.__main__',
    'sotto.main',
    'sotto.config',
    'sotto.core',
    'sotto.core.audio',
    'sotto.core.transcriber',
    'sotto.core.command_parser',
    'sotto.core.executor',
    'sotto.commands',
    'sotto.commands.registry',
    'sotto.ui',
    'sotto.ui.overlay',
    'sotto.ui.menubar',
    'sotto.ui.settings',
    # macOS specific
    'pynput.keyboard._darwin',
    'pynput.mouse._darwin',
    'AppKit',
    'Foundation',
    'Quartz',
    'objc',
    'PyObjCTools',
    'PyObjCTools.AppHelper',
    # Audio/ML
    'sounddevice',
    'rumps',
    'pydantic',
    'pydantic_settings',
    'yaml',
    'ctranslate2',
    'numpy',
]
hiddenimports += collect_submodules('pynput')
hiddenimports += collect_submodules('faster_whisper')
hiddenimports += collect_submodules('sotto')
hiddenimports += collect_submodules('rumps')

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'PIL'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Sotto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Sotto',
)

app = BUNDLE(
    coll,
    name='Sotto.app',
    icon=None,
    bundle_identifier='com.sotto.voicecontrol',
    info_plist={
        'CFBundleName': 'Sotto',
        'CFBundleDisplayName': 'Sotto',
        'CFBundleVersion': '0.2.0',
        'CFBundleShortVersionString': '0.2.0',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'LSMinimumSystemVersion': '11.0',
        'LSUIElement': True,  # Menubar app - hide from dock
        'LSBackgroundOnly': False,
        'NSHighResolutionCapable': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
        # Permission descriptions
        'NSMicrophoneUsageDescription': 'Sotto needs microphone access to hear your voice commands and dictation.',
        'NSAppleEventsUsageDescription': 'Sotto needs automation access to control applications and execute voice commands.',
        'NSSpeechRecognitionUsageDescription': 'Sotto uses local speech recognition to transcribe your voice.',
        # For accessibility (input monitoring)
        'NSAccessibilityUsageDescription': 'Sotto needs accessibility access to detect keyboard shortcuts and type text.',
    },
)
