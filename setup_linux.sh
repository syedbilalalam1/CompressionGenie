#!/bin/bash

# Update package list
sudo apt update

# Install Python 3.10
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip

# Install FFmpeg
sudo apt install -y ffmpeg

# Create and activate virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install required Python packages
pip install PyQt5 pyinstaller python-ffmpeg 