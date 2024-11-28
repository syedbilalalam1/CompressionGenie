# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Get the absolute path to FFmpeg binary
def get_ffmpeg_path():
    if sys.platform == 'win32':
        return './ffmpeg/bin/ffmpeg.exe'
    else:
        return './ffmpeg/bin/ffmpeg'

# Collect all required files
added_files = [
    # FFmpeg binaries
    (get_ffmpeg_path(), 'ffmpeg/bin'),
    ('ffmpeg/bin/ffprobe.exe' if sys.platform == 'win32' else 'ffmpeg/bin/ffprobe', 'ffmpeg/bin'),
    
    # Theme files
    ('themes/*.qss', 'themes'),
    
    # Settings and config files
    ('settings.json', '.'),
    
    # README
    ('README.txt', '.')
]

a = Analysis(
    ['video_compressor_ui.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VideoCompressor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico'  # Make sure you have an icon file
)
