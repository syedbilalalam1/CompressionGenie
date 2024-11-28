from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QCheckBox, QSpinBox,
                            QComboBox, QGroupBox, QFileDialog, QTabWidget,
                            QFormLayout)
from PyQt5.QtCore import Qt, QSettings
import os
import json

class AdvancedFFmpegSettings:
    def __init__(self):
        self.codec = 'libx264'
        self.pixel_format = 'yuv420p'
        self.threads = 0  # Auto
        self.tune = 'film'
        self.audio_codec = 'aac'
        self.audio_bitrate = '128k'

class Settings:
    def __init__(self):
        self.output_directory = ""
        self.enable_logging = True
        self.log_level = "INFO"
        self.temp_directory = ""
        self.delete_temp_files = True
        self.max_threads = 2
        self.ffmpeg = AdvancedFFmpegSettings()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = self.load_settings()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)

        layout = QVBoxLayout()
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # General Settings Tab
        general_tab = QWidget()
        general_layout = QVBoxLayout()
        
        # Output Directory Group
        output_group = QGroupBox("Output Directory")
        output_layout = QHBoxLayout()
        
        self.output_dir_edit = QLineEdit(self.settings.output_directory)
        self.output_dir_edit.setReadOnly(True)
        output_layout.addWidget(self.output_dir_edit)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(browse_btn)
        
        output_group.setLayout(output_layout)
        general_layout.addWidget(output_group)
        
        # Logging Group
        logging_group = QGroupBox("Logging")
        logging_layout = QFormLayout()
        
        self.enable_logging_cb = QCheckBox()
        self.enable_logging_cb.setChecked(self.settings.enable_logging)
        logging_layout.addRow("Enable Logging:", self.enable_logging_cb)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText(self.settings.log_level)
        logging_layout.addRow("Log Level:", self.log_level_combo)
        
        logging_group.setLayout(logging_layout)
        general_layout.addWidget(logging_group)
        
        # Temporary Files Group
        temp_group = QGroupBox("Temporary Files")
        temp_layout = QFormLayout()
        
        temp_dir_layout = QHBoxLayout()
        self.temp_dir_edit = QLineEdit(self.settings.temp_directory)
        self.temp_dir_edit.setReadOnly(True)
        temp_dir_layout.addWidget(self.temp_dir_edit)
        
        temp_browse_btn = QPushButton("Browse")
        temp_browse_btn.clicked.connect(self.browse_temp_dir)
        temp_dir_layout.addWidget(temp_browse_btn)
        
        temp_layout.addRow("Temp Directory:", temp_dir_layout)
        
        self.delete_temp_cb = QCheckBox()
        self.delete_temp_cb.setChecked(self.settings.delete_temp_files)
        temp_layout.addRow("Delete Temp Files:", self.delete_temp_cb)
        
        temp_group.setLayout(temp_layout)
        general_layout.addWidget(temp_group)
        
        general_tab.setLayout(general_layout)
        tab_widget.addTab(general_tab, "General")
        
        # FFmpeg Settings Tab
        ffmpeg_tab = QWidget()
        ffmpeg_layout = QFormLayout()
        
        # Video Settings
        video_group = QGroupBox("Video Settings")
        video_layout = QFormLayout()
        
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(['libx264', 'libx265', 'vp9'])
        self.codec_combo.setCurrentText(self.settings.ffmpeg.codec)
        video_layout.addRow("Video Codec:", self.codec_combo)
        
        self.pixel_format_combo = QComboBox()
        self.pixel_format_combo.addItems(['yuv420p', 'yuv444p', 'yuv422p'])
        self.pixel_format_combo.setCurrentText(self.settings.ffmpeg.pixel_format)
        video_layout.addRow("Pixel Format:", self.pixel_format_combo)
        
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(0, 32)
        self.threads_spin.setValue(self.settings.ffmpeg.threads)
        self.threads_spin.setSpecialValueText("Auto")
        video_layout.addRow("Threads:", self.threads_spin)
        
        self.tune_combo = QComboBox()
        self.tune_combo.addItems(['film', 'animation', 'grain', 'stillimage', 'fastdecode', 'zerolatency'])
        self.tune_combo.setCurrentText(self.settings.ffmpeg.tune)
        video_layout.addRow("Tune:", self.tune_combo)
        
        video_group.setLayout(video_layout)
        ffmpeg_layout.addWidget(video_group)
        
        # Audio Settings
        audio_group = QGroupBox("Audio Settings")
        audio_layout = QFormLayout()
        
        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.addItems(['aac', 'libmp3lame', 'copy'])
        self.audio_codec_combo.setCurrentText(self.settings.ffmpeg.audio_codec)
        audio_layout.addRow("Audio Codec:", self.audio_codec_combo)
        
        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.addItems(['64k', '128k', '192k', '256k', '320k'])
        self.audio_bitrate_combo.setCurrentText(self.settings.ffmpeg.audio_bitrate)
        audio_layout.addRow("Audio Bitrate:", self.audio_bitrate_combo)
        
        audio_group.setLayout(audio_layout)
        ffmpeg_layout.addWidget(audio_group)
        
        ffmpeg_tab.setLayout(ffmpeg_layout)
        tab_widget.addTab(ffmpeg_tab, "FFmpeg")
        
        layout.addWidget(tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory",
            self.output_dir_edit.text()
        )
        if directory:
            self.output_dir_edit.setText(directory)

    def browse_temp_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Temporary Directory",
            self.temp_dir_edit.text()
        )
        if directory:
            self.temp_dir_edit.setText(directory)

    def load_settings(self):
        settings = Settings()
        try:
            with open('settings.json', 'r') as f:
                data = json.load(f)
                settings.output_directory = data.get('output_directory', '')
                settings.enable_logging = data.get('enable_logging', True)
                settings.log_level = data.get('log_level', 'INFO')
                settings.temp_directory = data.get('temp_directory', '')
                settings.delete_temp_files = data.get('delete_temp_files', True)
                settings.max_threads = data.get('max_threads', 2)
                
                ffmpeg_settings = data.get('ffmpeg', {})
                settings.ffmpeg.codec = ffmpeg_settings.get('codec', 'libx264')
                settings.ffmpeg.pixel_format = ffmpeg_settings.get('pixel_format', 'yuv420p')
                settings.ffmpeg.threads = ffmpeg_settings.get('threads', 0)
                settings.ffmpeg.tune = ffmpeg_settings.get('tune', 'film')
                settings.ffmpeg.audio_codec = ffmpeg_settings.get('audio_codec', 'aac')
                settings.ffmpeg.audio_bitrate = ffmpeg_settings.get('audio_bitrate', '128k')
        except:
            pass
        return settings

    def save_settings(self):
        self.settings.output_directory = self.output_dir_edit.text()
        self.settings.enable_logging = self.enable_logging_cb.isChecked()
        self.settings.log_level = self.log_level_combo.currentText()
        self.settings.temp_directory = self.temp_dir_edit.text()
        self.settings.delete_temp_files = self.delete_temp_cb.isChecked()
        
        self.settings.ffmpeg.codec = self.codec_combo.currentText()
        self.settings.ffmpeg.pixel_format = self.pixel_format_combo.currentText()
        self.settings.ffmpeg.threads = self.threads_spin.value()
        self.settings.ffmpeg.tune = self.tune_combo.currentText()
        self.settings.ffmpeg.audio_codec = self.audio_codec_combo.currentText()
        self.settings.ffmpeg.audio_bitrate = self.audio_bitrate_combo.currentText()
        
        try:
            with open('settings.json', 'w') as f:
                json.dump({
                    'output_directory': self.settings.output_directory,
                    'enable_logging': self.settings.enable_logging,
                    'log_level': self.settings.log_level,
                    'temp_directory': self.settings.temp_directory,
                    'delete_temp_files': self.settings.delete_temp_files,
                    'max_threads': self.settings.max_threads,
                    'ffmpeg': {
                        'codec': self.settings.ffmpeg.codec,
                        'pixel_format': self.settings.ffmpeg.pixel_format,
                        'threads': self.settings.ffmpeg.threads,
                        'tune': self.settings.ffmpeg.tune,
                        'audio_codec': self.settings.ffmpeg.audio_codec,
                        'audio_bitrate': self.settings.ffmpeg.audio_bitrate
                    }
                }, f, indent=4)
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")
            return
            
        self.accept() 