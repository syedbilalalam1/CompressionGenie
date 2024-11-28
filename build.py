import os
import sys
import shutil
import subprocess
import requests
from zipfile import ZipFile
from pathlib import Path
import json

def check_ffmpeg_in_path():
    """Check if FFmpeg is available in system PATH"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True)
        return True
    except FileNotFoundError:
        return False

def create_readme():
    """Create README.txt file"""
    readme_content = """Video Compressor
Created by Syed Bilal Alam

A powerful tool for compressing video files using FFmpeg.

Features:
- Batch video compression
- Multiple quality presets
- Custom compression settings
- Dark/Light theme support
- Advanced FFmpeg options

Usage:
1. Drag and drop video files or use 'Select Files' button
2. Choose compression settings
3. Click 'Compress' to start processing

Note: This application uses FFmpeg for video processing.
Copyright © 2024 Syed Bilal Alam. All rights reserved.
"""
    
    # Create README in the project directory
    with open('README.txt', 'w') as f:
        f.write(readme_content)

def download_ffmpeg():
    """Download FFmpeg binaries if not already present"""
    ffmpeg_dir = Path('ffmpeg')
    
    # Check if FFmpeg is already downloaded
    if ffmpeg_dir.exists() and (ffmpeg_dir / 'bin' / 'ffmpeg.exe').exists():
        print("FFmpeg already downloaded, skipping...")
        return
    
    # Check if FFmpeg is in PATH
    if check_ffmpeg_in_path():
        print("FFmpeg found in PATH, creating symbolic links...")
        ffmpeg_dir.mkdir(exist_ok=True)
        bin_dir = ffmpeg_dir / 'bin'
        bin_dir.mkdir(exist_ok=True)
        
        if sys.platform == 'win32':
            # Find FFmpeg in PATH
            result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True)
            ffmpeg_path = result.stdout.strip().split('\n')[0]
            result = subprocess.run(['where', 'ffprobe'], capture_output=True, text=True)
            ffprobe_path = result.stdout.strip().split('\n')[0]
            
            # Copy FFmpeg files instead of symlinks on Windows
            shutil.copy2(ffmpeg_path, str(bin_dir / 'ffmpeg.exe'))
            shutil.copy2(ffprobe_path, str(bin_dir / 'ffprobe.exe'))
        else:
            # Create symlinks on Unix systems
            ffmpeg_path = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True).stdout.strip()
            ffprobe_path = subprocess.run(['which', 'ffprobe'], capture_output=True, text=True).stdout.strip()
            os.symlink(ffmpeg_path, str(bin_dir / 'ffmpeg'))
            os.symlink(ffprobe_path, str(bin_dir / 'ffprobe'))
        return
    
    # Download FFmpeg if not found
    if sys.platform == 'win32':
        print("FFmpeg not found, downloading...")
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        zip_path = "ffmpeg.zip"
        
        try:
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(zip_path, 'wb') as f:
                if total_size == 0:
                    f.write(response.content)
                else:
                    downloaded = 0
                    total_size = int(total_size)
                    for data in response.iter_content(chunk_size=4096):
                        downloaded += len(data)
                        f.write(data)
                        done = int(50 * downloaded / total_size)
                        sys.stdout.write('\r[{}{}]'.format('█' * done, '.' * (50-done)))
                        sys.stdout.flush()
            print("\nExtracting FFmpeg...")
            
            with ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall('.')
            
            # Organize FFmpeg files
            ffmpeg_dir.mkdir(exist_ok=True)
            bin_dir = ffmpeg_dir / 'bin'
            bin_dir.mkdir(exist_ok=True)
            
            extracted_dir = next(Path('.').glob('ffmpeg-master-*'))
            shutil.move(str(extracted_dir / 'bin' / 'ffmpeg.exe'), str(bin_dir / 'ffmpeg.exe'))
            shutil.move(str(extracted_dir / 'bin' / 'ffprobe.exe'), str(bin_dir / 'ffprobe.exe'))
            
            # Cleanup
            shutil.rmtree(extracted_dir)
            os.remove(zip_path)
            
        except Exception as e:
            print(f"Error downloading FFmpeg: {e}")
            sys.exit(1)
    else:
        print("FFmpeg must be installed on non-Windows systems.")
        print("Please install FFmpeg using your package manager.")
        sys.exit(1)

def create_default_settings():
    """Create default settings.json if it doesn't exist"""
    if not os.path.exists('settings.json'):
        default_settings = {
            "output_directory": "",
            "enable_logging": True,
            "log_level": "INFO",
            "temp_directory": "",
            "delete_temp_files": True,
            "max_threads": 2,
            "theme": "light",
            "ffmpeg": {
                "codec": "libx264",
                "pixel_format": "yuv420p",
                "threads": 0,
                "tune": "film",
                "audio_codec": "aac",
                "audio_bitrate": "128k"
            }
        }
        
        with open('settings.json', 'w') as f:
            json.dump(default_settings, f, indent=4)
        print("Created default settings.json")

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable...")
    
    # Clean previous build
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    
    # Ensure README exists and create dist directory structure
    create_readme()
    dist_dir = Path('dist') / 'VideoCompressor'
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy README to dist directory before running PyInstaller
    shutil.copy2('README.txt', str(dist_dir / 'README.txt'))
    
    # Run PyInstaller
    try:
        result = subprocess.run(['pyinstaller', 'video_compressor.spec', '--clean'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error building executable: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during build: {e}")
        sys.exit(1)

    print("Build completed successfully!")

def create_theme_files():
    """Create theme files if they don't exist"""
    themes_dir = Path('themes')
    themes_dir.mkdir(exist_ok=True)

    # Light theme
    light_theme = """
/* Light Theme */
QMainWindow {
    background-color: #f5f5f5;
}

QLabel {
    color: #2c3e50;
    font-size: 12px;
}

QPushButton {
    background-color: #3498db;
    color: white;
    border: none;
    padding: 8px 15px;
    border-radius: 5px;
    font-weight: bold;
    min-width: 100px;
}

QPushButton:hover {
    background-color: #2980b9;
}

QPushButton:disabled {
    background-color: #bdc3c7;
}

QProgressBar {
    border: 2px solid #3498db;
    border-radius: 5px;
    text-align: center;
    background-color: #ffffff;
    height: 20px;
}

QProgressBar::chunk {
    background-color: #3498db;
    border-radius: 3px;
}

QComboBox {
    border: 2px solid #3498db;
    border-radius: 5px;
    padding: 5px;
    background-color: white;
    min-width: 150px;
}

QComboBox:hover {
    border-color: #2980b9;
}

QSpinBox {
    border: 2px solid #3498db;
    border-radius: 5px;
    padding: 5px;
    background-color: white;
}

QTableWidget {
    background-color: white;
    alternate-background-color: #ecf0f1;
    border: 2px solid #3498db;
    border-radius: 5px;
}

QTableWidget::item {
    padding: 8px;
}

QHeaderView::section {
    background-color: #3498db;
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
}

/* Drop Area Styling */
QLabel#dropArea {
    border: 3px dashed #3498db;
    border-radius: 10px;
    padding: 30px;
    background-color: #ecf0f1;
    font-size: 14px;
    font-weight: bold;
    color: #2c3e50;
}

QLabel#dropArea:hover {
    background-color: #d5dbdb;
    border-color: #2980b9;
}

/* Status Label */
QLabel#statusLabel {
    font-size: 13px;
    color: #2c3e50;
    font-weight: bold;
}

/* Group Box Styling */
QGroupBox {
    border: 2px solid #3498db;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 15px;
    font-weight: bold;
}

QGroupBox::title {
    color: #2c3e50;
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 10px;
}
"""

    # Dark theme
    dark_theme = """
/* Dark Theme */
QMainWindow {
    background-color: #2c3e50;
}

QLabel {
    color: #ecf0f1;
    font-size: 12px;
}

QPushButton {
    background-color: #3498db;
    color: white;
    border: none;
    padding: 8px 15px;
    border-radius: 5px;
    font-weight: bold;
    min-width: 100px;
}

QPushButton:hover {
    background-color: #2980b9;
}

QPushButton:disabled {
    background-color: #34495e;
}

QProgressBar {
    border: 2px solid #3498db;
    border-radius: 5px;
    text-align: center;
    background-color: #34495e;
    height: 20px;
}

QProgressBar::chunk {
    background-color: #3498db;
    border-radius: 3px;
}

QComboBox {
    border: 2px solid #3498db;
    border-radius: 5px;
    padding: 5px;
    background-color: #34495e;
    color: white;
    min-width: 150px;
}

QComboBox:hover {
    border-color: #2980b9;
}

QSpinBox {
    border: 2px solid #3498db;
    border-radius: 5px;
    padding: 5px;
    background-color: #34495e;
    color: white;
}

QTableWidget {
    background-color: #34495e;
    alternate-background-color: #2c3e50;
    border: 2px solid #3498db;
    border-radius: 5px;
    color: white;
}

QTableWidget::item {
    padding: 8px;
}

QHeaderView::section {
    background-color: #3498db;
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
}

/* Drop Area Styling */
QLabel#dropArea {
    border: 3px dashed #3498db;
    border-radius: 10px;
    padding: 30px;
    background-color: #34495e;
    font-size: 14px;
    font-weight: bold;
    color: white;
}

QLabel#dropArea:hover {
    background-color: #2c3e50;
    border-color: #2980b9;
}

/* Status Label */
QLabel#statusLabel {
    font-size: 13px;
    color: white;
    font-weight: bold;
}

/* Group Box Styling */
QGroupBox {
    border: 2px solid #3498db;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 15px;
    font-weight: bold;
    color: white;
}

QGroupBox::title {
    color: white;
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 10px;
}
"""

    # Write theme files
    with open(themes_dir / 'light_theme.qss', 'w') as f:
        f.write(light_theme)
    
    with open(themes_dir / 'dark_theme.qss', 'w') as f:
        f.write(dark_theme)

def main():
    """Main build process"""
    try:
        # Ensure required directories exist
        for dir_name in ['themes', 'assets']:
            os.makedirs(dir_name, exist_ok=True)
        
        # Create theme files
        create_theme_files()
        
        # Create default settings file
        create_default_settings()
        
        # Handle FFmpeg
        download_ffmpeg()
        
        # Build executable
        build_executable()
        
        print(f"Executable can be found in: {os.path.abspath('dist/VideoCompressor')}")
    except Exception as e:
        print(f"Build failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()