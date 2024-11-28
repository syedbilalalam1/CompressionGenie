import sys
import subprocess
from PyQt5.QtWidgets import QApplication, QMessageBox

def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True)
        return True
    except FileNotFoundError:
        return False

def verify_setup():
    app = QApplication(sys.argv)
    
    # Check Python version
    python_version = sys.version_info
    python_ok = python_version.major == 3 and python_version.minor >= 10
    
    # Check FFmpeg
    ffmpeg_ok = check_ffmpeg()
    
    # Create message
    message = "Setup Verification Results:\n\n"
    message += f"Python 3.10+: {'✓' if python_ok else '✗'}\n"
    message += f"FFmpeg: {'✓' if ffmpeg_ok else '✗'}\n"
    message += f"PyQt5: ✓\n"
    
    QMessageBox.information(None, "Setup Verification", message)
    
if __name__ == '__main__':
    verify_setup() 