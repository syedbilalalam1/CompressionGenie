#!/bin/bash

# Install Homebrew if not installed
if ! command -v brew &> /dev/null; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install Python 3.10
brew install python@3.10

# Install FFmpeg
brew install ffmpeg

# Create and activate virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install required Python packages
pip install PyQt5 pyinstaller python-ffmpeg 