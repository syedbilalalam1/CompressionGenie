import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QPushButton, QProgressBar, QFileDialog, QLabel, 
                            QMessageBox, QComboBox, QHBoxLayout, QSpinBox, QFrame, 
                            QTableWidget, QTableWidgetItem, QHeaderView, QDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QThreadPool
from PyQt5.QtGui import QDropEvent, QDragEnterEvent, QIcon
from video_compressor import compress_video, VideoPreset
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
import uuid
import json
from settings_dialog import SettingsDialog

@dataclass
class QualityPreset:
    name: str
    resolution: Optional[Tuple[int, int]]
    bitrate: Optional[str]
    crf: int
    preset: VideoPreset

QUALITY_PRESETS = {
    'Low Quality': QualityPreset(
        name='Low Quality',
        resolution=(854, 480),  # 480p
        bitrate='1M',
        crf=28,
        preset=VideoPreset.FAST
    ),
    'Medium Quality': QualityPreset(
        name='Medium Quality',
        resolution=(1280, 720),  # 720p
        bitrate='2M',
        crf=23,
        preset=VideoPreset.BALANCED
    ),
    'High Quality': QualityPreset(
        name='High Quality',
        resolution=(1920, 1080),  # 1080p
        bitrate='4M',
        crf=18,
        preset=VideoPreset.BEST
    ),
    'Custom': QualityPreset(
        name='Custom',
        resolution=None,
        bitrate=None,
        crf=23,
        preset=VideoPreset.BALANCED
    )
}

@dataclass
class CompressionTask:
    input_path: str
    output_path: str
    preset: VideoPreset
    crf: int
    resolution: Optional[Tuple[int, int]] = None
    bitrate: Optional[str] = None
    progress: int = 0
    status: str = "Pending"

class CompressionManager:
    def __init__(self, max_threads=2):
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(max_threads)
        self.tasks: Dict[str, CompressionTask] = {}
        self.active_workers: List[CompressionWorker] = []

class DropArea(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setText("Drag and drop video files here\nor click 'Select Files'")
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 30px;
                background: #f0f0f0;
            }
            QLabel:hover {
                background: #e0e0e0;
                border-color: #999;
            }
        """)
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #4CAF50;
                    border-radius: 5px;
                    padding: 30px;
                    background: #E8F5E9;
                }
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 30px;
                background: #f0f0f0;
            }
            QLabel:hover {
                background: #e0e0e0;
                border-color: #999;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        valid_files = self.validate_files(files)
        
        if valid_files:
            self.parent().set_input_files(valid_files)
        
        # Reset style
        self.dragLeaveEvent(None)

    def validate_files(self, files):
        """Validate dropped files are supported video formats"""
        valid_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'}
        valid_files = []
        invalid_files = []

        for file_path in files:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in valid_extensions:
                valid_files.append(file_path)
            else:
                invalid_files.append(os.path.basename(file_path))

        if invalid_files:
            QMessageBox.warning(
                self,
                "Invalid Files",
                f"The following files are not supported:\n{', '.join(invalid_files)}\n\n"
                f"Supported formats: {', '.join(valid_extensions)}"
            )

        return valid_files

    def mousePressEvent(self, event):
        """Make the drop area clickable to open file dialog"""
        if event.button() == Qt.LeftButton:
            self.parent().select_files()

class CompressionWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    percentage = pyqtSignal(int)
    task_id = pyqtSignal(str)

    def __init__(self, task_id: str, *args, **kwargs):
        super().__init__()
        self.task_id = task_id
        self.input_path = kwargs.get('input_path')
        self.output_path = kwargs.get('output_path')
        self.preset = kwargs.get('preset')
        self.crf = kwargs.get('crf')
        self.resolution = kwargs.get('resolution')
        self.bitrate = kwargs.get('bitrate')

    def progress_handler(self, output):
        self.progress.emit(output)
        # Try to parse FFmpeg output for time progress
        if "time=" in output:
            try:
                time_str = output.split("time=")[1].split()[0]
                # Convert time to seconds
                h, m, s = map(float, time_str.split(':'))
                current_time = h * 3600 + m * 60 + s
                
                # Emit percentage based on duration (if known)
                if hasattr(self, 'duration'):
                    percentage = min(int((current_time / self.duration) * 100), 100)
                    self.percentage.emit(percentage)
            except:
                pass

    def run(self):
        # Get video duration first
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                 '-of', 'default=noprint_wrappers=1:nokey=1', self.input_path],
                capture_output=True,
                text=True
            )
            self.duration = float(result.stdout)
        except:
            self.duration = 0

        self.progress.emit(f"Processing {os.path.basename(self.input_path)}...")
        success, message = compress_video(
            input_path=self.input_path,
            output_path=self.output_path,
            preset=self.preset,
            crf=self.crf,
            resolution=self.resolution,
            bitrate=self.bitrate,
            progress_callback=self.progress_handler
        )
        self.finished.emit(success, message)

class VideoCompressorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_theme = 'light'
        self.load_theme_preference()
        self.input_files = []
        self.current_file_index = 0
        self.total_files = 0
        
        max_threads = max(1, os.cpu_count() - 1)
        self.compression_manager = CompressionManager(max_threads)
        
        self.initUI()
        self.apply_theme(self.current_theme)

    def initUI(self):
        self.setWindowTitle('Video Compressor - by Syed Bilal Alam')
        self.setMinimumSize(500, 400)

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Add theme toggle button to the top of the layout
        theme_layout = QHBoxLayout()
        
        self.theme_btn = QPushButton()
        self.theme_btn.setCheckable(True)
        self.theme_btn.setChecked(self.current_theme == 'dark')
        self.update_theme_button()
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.theme_btn.setFixedSize(40, 40)
        theme_layout.addWidget(self.theme_btn)
        theme_layout.addStretch()
        
        layout.insertLayout(0, theme_layout)

        # Drop area
        self.drop_area = DropArea()
        layout.addWidget(self.drop_area)

        # File selection button
        self.select_btn = QPushButton('Select Files')
        self.select_btn.clicked.connect(self.select_files)
        layout.addWidget(self.select_btn)

        # Add file list display
        self.file_list_label = QLabel('No files selected')
        self.file_list_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.file_list_label)

        # Add batch progress
        self.batch_progress = QProgressBar()
        self.batch_progress.setTextVisible(True)
        self.batch_progress.setAlignment(Qt.AlignCenter)
        self.batch_progress.setValue(0)
        self.batch_progress.setFormat('Overall Progress: %p%')
        layout.addWidget(self.batch_progress)

        # Compression settings
        settings_layout = QHBoxLayout()

        # Add quality preset dropdown at the top of settings
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel('Quality Preset:'))
        self.quality_preset_combo = QComboBox()
        self.quality_preset_combo.addItems(QUALITY_PRESETS.keys())
        self.quality_preset_combo.setCurrentText('Medium Quality')
        self.quality_preset_combo.currentTextChanged.connect(self.on_quality_preset_change)
        quality_layout.addWidget(self.quality_preset_combo)
        settings_layout.addLayout(quality_layout)

        # Add a separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        settings_layout.addWidget(line)

        # Preset selection
        self.preset_combo = QComboBox()
        for preset in VideoPreset:
            self.preset_combo.addItem(preset.name, preset)
        self.preset_combo.setCurrentText('BALANCED')
        settings_layout.addWidget(QLabel('Preset:'))
        settings_layout.addWidget(self.preset_combo)

        # Quality settings (CRF)
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(23)
        self.crf_spin.setToolTip('Lower value = Better quality (0-51)')
        settings_layout.addWidget(QLabel('Quality:'))
        settings_layout.addWidget(self.crf_spin)

        # Enhanced resolution controls
        resolution_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel('Resolution:'))
        
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(['Original', '1080p', '720p', '480p', 'Custom'])
        self.resolution_combo.currentTextChanged.connect(self.on_resolution_change)
        resolution_layout.addWidget(self.resolution_combo)
        
        # Custom resolution inputs
        self.width_input = QSpinBox()
        self.width_input.setRange(128, 7680)  # 8K max
        self.width_input.setValue(1920)
        self.width_input.setEnabled(False)
        resolution_layout.addWidget(self.width_input)
        
        resolution_layout.addWidget(QLabel('x'))
        
        self.height_input = QSpinBox()
        self.height_input.setRange(128, 4320)  # 8K max
        self.height_input.setValue(1080)
        self.height_input.setEnabled(False)
        resolution_layout.addWidget(self.height_input)
        
        settings_layout.addLayout(resolution_layout)

        # Enhanced bitrate controls
        bitrate_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel('Bitrate:'))
        
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(['Auto', 'Custom', '8M', '4M', '2M', '1M'])
        self.bitrate_combo.currentTextChanged.connect(self.on_bitrate_change)
        bitrate_layout.addWidget(self.bitrate_combo)
        
        self.bitrate_input = QSpinBox()
        self.bitrate_input.setRange(100, 50000)  # 100Kbps to 50Mbps
        self.bitrate_input.setValue(2000)
        self.bitrate_input.setSuffix(' Kbps')
        self.bitrate_input.setEnabled(False)
        bitrate_layout.addWidget(self.bitrate_input)
        
        settings_layout.addLayout(bitrate_layout)

        layout.addLayout(settings_layout)

        # Add concurrent processing control
        concurrent_layout = QHBoxLayout()
        concurrent_layout.addWidget(QLabel('Concurrent Tasks:'))
        
        self.thread_count_spin = QSpinBox()
        self.thread_count_spin.setRange(1, os.cpu_count())
        self.thread_count_spin.setValue(self.compression_manager.thread_pool.maxThreadCount())
        self.thread_count_spin.valueChanged.connect(self.update_thread_count)
        concurrent_layout.addWidget(self.thread_count_spin)
        
        layout.addLayout(concurrent_layout)

        # Add task list view
        self.task_list = QTableWidget()
        self.task_list.setColumnCount(4)
        self.task_list.setHorizontalHeaderLabels(['File', 'Status', 'Progress', 'Actions'])
        self.task_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.task_list)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Compress button
        self.compress_btn = QPushButton('Compress')
        self.compress_btn.clicked.connect(self.start_compression)
        self.compress_btn.setEnabled(False)
        layout.addWidget(self.compress_btn)

        # Add settings button to toolbar or menu
        settings_btn = QPushButton('Settings')
        settings_btn.clicked.connect(self.show_settings)
        theme_layout.addWidget(settings_btn)
        
        # Add About button next to Settings
        about_btn = QPushButton('About')
        about_btn.clicked.connect(self.show_about)
        theme_layout.addWidget(about_btn)
        
        self.show()

    def select_files(self):
        """Handle multiple file selection"""
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Video Files",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*.*)"
        )
        if file_names:
            self.set_input_files(file_names)

    def set_input_files(self, file_paths):
        """Handle multiple input files"""
        self.input_files = file_paths
        self.total_files = len(file_paths)
        self.current_file_index = 0
        
        # Update UI with file list
        if self.total_files == 0:
            self.file_list_label.setText('No files selected')
            self.compress_btn.setEnabled(False)
        elif self.total_files == 1:
            self.file_list_label.setText(
                f"Selected: {os.path.basename(file_paths[0])}"
            )
            self.compress_btn.setEnabled(True)
        else:
            # Create a formatted list of files
            file_list = "\n".join([
                f"{i+1}. {os.path.basename(path)}"
                for i, path in enumerate(file_paths[:5])
            ])
            if self.total_files > 5:
                file_list += f"\n... and {self.total_files - 5} more files"
            
            self.file_list_label.setText(
                f"Selected {self.total_files} files:\n{file_list}"
            )
            self.compress_btn.setEnabled(True)
        
        # Reset progress indicators
        self.status_label.setText('')
        self.progress_bar.setValue(0)
        self.batch_progress.setValue(0)

        # Update drop area text
        self.drop_area.setText(
            "Drop more files here or click to select files"
            if self.total_files > 0
            else "Drag and drop video files here\nor click 'Select Files'"
        )

    def on_resolution_change(self, value):
        """Enable/disable custom resolution inputs based on selection"""
        is_custom = value == 'Custom'
        self.width_input.setEnabled(is_custom)
        self.height_input.setEnabled(is_custom)

    def on_bitrate_change(self, value):
        """Enable/disable custom bitrate input based on selection"""
        self.bitrate_input.setEnabled(value == 'Custom')

    def get_resolution(self):
        """Get resolution settings with validation"""
        resolution_map = {
            '1080p': (1920, 1080),
            '720p': (1280, 720),
            '480p': (854, 480)
        }
        selected = self.resolution_combo.currentText()
        
        if selected == 'Original':
            return None
        elif selected == 'Custom':
            width = self.width_input.value()
            height = self.height_input.value()
            # Validate aspect ratio
            if not self.validate_aspect_ratio(width, height):
                raise ValueError("Invalid aspect ratio. Please use standard video dimensions.")
            return (width, height)
        else:
            return resolution_map.get(selected)

    def get_bitrate(self):
        """Get bitrate settings with validation"""
        selected = self.bitrate_combo.currentText()
        
        if selected == 'Auto':
            return None
        elif selected == 'Custom':
            # Convert Kbps to FFmpeg format (e.g., 2000 Kbps -> 2M)
            kbps = self.bitrate_input.value()
            return f"{kbps//1000}M" if kbps >= 1000 else f"{kbps}K"
        else:
            return selected

    def validate_aspect_ratio(self, width, height):
        """Validate if the aspect ratio is reasonable for video"""
        ratio = width / height
        # Common aspect ratios: 16:9, 4:3, 21:9
        common_ratios = [16/9, 4/3, 21/9]
        return any(abs(ratio - r) < 0.1 for r in common_ratios)

    def validate_settings(self):
        """Validate all compression settings before starting"""
        try:
            # Skip validation for preset quality settings
            if self.quality_preset_combo.currentText() != 'Custom':
                return True

            if self.resolution_combo.currentText() == 'Custom':
                width = self.width_input.value()
                height = self.height_input.value()
                if width % 2 != 0 or height % 2 != 0:
                    raise ValueError("Width and height must be even numbers")
                if not self.validate_aspect_ratio(width, height):
                    raise ValueError("Invalid aspect ratio")

            if self.bitrate_combo.currentText() == 'Custom':
                bitrate = self.bitrate_input.value()
                if bitrate < 100:
                    raise ValueError("Bitrate must be at least 100 Kbps")

            return True
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Settings", str(e))
            return False

    def start_compression(self):
        if not self.input_files:
            return

        if not self.validate_settings():
            return

        # Create compression tasks for all files
        for input_path in self.input_files:
            base_name, ext = os.path.splitext(input_path)
            output_path = f"{base_name}_compressed{ext}"
            
            # Get compression settings
            preset_name = self.quality_preset_combo.currentText()
            if preset_name != 'Custom':
                preset_config = QUALITY_PRESETS[preset_name]
                preset = preset_config.preset
                crf = preset_config.crf
                resolution = preset_config.resolution
                bitrate = preset_config.bitrate
            else:
                preset = self.preset_combo.currentData()
                crf = self.crf_spin.value()
                resolution = self.get_resolution()
                bitrate = self.get_bitrate()

            # Create task
            task = CompressionTask(
                input_path=input_path,
                output_path=output_path,
                preset=preset,
                crf=crf,
                resolution=resolution,
                bitrate=bitrate
            )
            
            # Add to task manager
            task_id = str(uuid.uuid4())
            self.compression_manager.tasks[task_id] = task
            
            # Add to task list UI
            self.add_task_to_list(task_id, task)
            
            # Start task if possible
            self.try_start_task(task_id)

    def add_task_to_list(self, task_id: str, task: CompressionTask):
        """Add task to the UI task list"""
        row = self.task_list.rowCount()
        self.task_list.insertRow(row)
        
        # File name
        self.task_list.setItem(row, 0, QTableWidgetItem(
            os.path.basename(task.input_path)
        ))
        
        # Status
        self.task_list.setItem(row, 1, QTableWidgetItem(task.status))
        
        # Progress
        progress = QProgressBar()
        progress.setValue(0)
        self.task_list.setCellWidget(row, 2, progress)
        
        # Cancel button
        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(lambda: self.cancel_task(task_id))
        self.task_list.setCellWidget(row, 3, cancel_btn)

    def try_start_task(self, task_id: str):
        """Try to start a compression task if resources are available"""
        if (len(self.compression_manager.active_workers) < 
            self.compression_manager.thread_pool.maxThreadCount()):
            
            task = self.compression_manager.tasks[task_id]
            
            # Create and configure worker
            worker = CompressionWorker(
                task_id,
                input_path=task.input_path,
                output_path=task.output_path,
                preset=task.preset,
                crf=task.crf,
                resolution=task.resolution,
                bitrate=task.bitrate
            )
            
            # Connect signals
            worker.progress.connect(lambda msg: self.update_task_status(task_id, msg))
            worker.percentage.connect(lambda p: self.update_task_progress(task_id, p))
            worker.finished.connect(lambda s, m: self.task_finished(task_id, s, m))
            
            # Start worker
            worker.start()
            self.compression_manager.active_workers.append(worker)
            
            # Update UI
            self.update_task_status(task_id, "Processing...")

    def update_task_status(self, task_id: str, status: str):
        """Update the status of a task in the UI"""
        task = self.compression_manager.tasks[task_id]
        task.status = status
        
        # Find task row
        for row in range(self.task_list.rowCount()):
            if self.task_list.item(row, 0).text() == os.path.basename(task.input_path):
                self.task_list.item(row, 1).setText(status)
                break

    def update_task_progress(self, task_id: str, progress: int):
        """Update the progress of a task in the UI"""
        task = self.compression_manager.tasks[task_id]
        task.progress = progress
        
        # Find task row and update progress bar
        for row in range(self.task_list.rowCount()):
            if self.task_list.item(row, 0).text() == os.path.basename(task.input_path):
                progress_bar = self.task_list.cellWidget(row, 2)
                progress_bar.setValue(progress)
                break

    def task_finished(self, task_id: str, success: bool, message: str):
        """Handle task completion"""
        status = "Completed" if success else "Failed"
        self.update_task_status(task_id, status)
        
        # Remove from active workers
        self.compression_manager.active_workers = [
            w for w in self.compression_manager.active_workers 
            if w.task_id != task_id
        ]
        
        # Start next task if available
        pending_tasks = [
            tid for tid, task in self.compression_manager.tasks.items()
            if task.status == "Pending"
        ]
        if pending_tasks:
            self.try_start_task(pending_tasks[0])
        
        # Show completion message if all tasks are done
        if not self.compression_manager.active_workers:
            QMessageBox.information(
                self,
                "Compression Complete",
                "All compression tasks completed!"
            )

    def cancel_task(self, task_id: str):
        """Cancel a compression task"""
        task = self.compression_manager.tasks[task_id]
        
        # Stop worker if active
        for worker in self.compression_manager.active_workers:
            if worker.task_id == task_id:
                worker.terminate()
                worker.wait()
                self.compression_manager.active_workers.remove(worker)
                break
        
        # Update status
        self.update_task_status(task_id, "Cancelled")
        
        # Try to start next task
        pending_tasks = [
            tid for tid, task in self.compression_manager.tasks.items()
            if task.status == "Pending"
        ]
        if pending_tasks:
            self.try_start_task(pending_tasks[0])

    def update_thread_count(self, value):
        """Update the maximum number of concurrent compression tasks"""
        self.compression_manager.thread_pool.setMaxThreadCount(value)

    def on_quality_preset_change(self, preset_name: str):
        """Handle quality preset selection"""
        if preset_name == 'Custom':
            # Enable all custom controls
            self.preset_combo.setEnabled(True)
            self.crf_spin.setEnabled(True)
            self.resolution_combo.setEnabled(True)
            self.bitrate_combo.setEnabled(True)
            return

        # Get preset settings
        preset = QUALITY_PRESETS[preset_name]

        # Update compression preset
        self.preset_combo.setCurrentText(preset.preset.name)
        self.preset_combo.setEnabled(False)

        # Update CRF
        self.crf_spin.setValue(preset.crf)
        self.crf_spin.setEnabled(False)

        # Update resolution
        if preset.resolution:
            width, height = preset.resolution
            if (width, height) == (1920, 1080):
                self.resolution_combo.setCurrentText('1080p')
            elif (width, height) == (1280, 720):
                self.resolution_combo.setCurrentText('720p')
            elif (width, height) == (854, 480):
                self.resolution_combo.setCurrentText('480p')
        else:
            self.resolution_combo.setCurrentText('Original')
        self.resolution_combo.setEnabled(False)
        self.width_input.setEnabled(False)
        self.height_input.setEnabled(False)

        # Update bitrate
        if preset.bitrate:
            self.bitrate_combo.setCurrentText(preset.bitrate)
        else:
            self.bitrate_combo.setCurrentText('Auto')
        self.bitrate_combo.setEnabled(False)
        self.bitrate_input.setEnabled(False)

    def load_theme_preference(self):
        """Load saved theme preference"""
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                self.current_theme = settings.get('theme', 'light')
        except:
            self.current_theme = 'light'

    def save_theme_preference(self):
        """Save current theme preference"""
        try:
            settings = {'theme': self.current_theme}
            with open('settings.json', 'w') as f:
                json.dump(settings, f)
        except:
            pass

    def toggle_theme(self):
        """Toggle between light and dark themes"""
        self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
        self.apply_theme(self.current_theme)
        self.update_theme_button()
        self.save_theme_preference()

    def apply_theme(self, theme_name):
        """Apply the specified theme"""
        try:
            # Load theme file
            theme_file = f'themes/{theme_name}_theme.qss'
            with open(theme_file, 'r') as f:
                self.setStyleSheet(f.read())
            
            # Update drop area style based on theme
            if theme_name == 'dark':
                self.drop_area.setStyleSheet("""
                    QLabel {
                        border: 2px dashed #555555;
                        border-radius: 5px;
                        padding: 30px;
                        background: #2d2d2d;
                        color: white;
                    }
                    QLabel:hover {
                        background: #353535;
                        border-color: #666666;
                    }
                """)
            else:
                self.drop_area.setStyleSheet("""
                    QLabel {
                        border: 2px dashed #aaa;
                        border-radius: 5px;
                        padding: 30px;
                        background: #f0f0f0;
                    }
                    QLabel:hover {
                        background: #e0e0e0;
                        border-color: #999;
                    }
                """)
        except Exception as e:
            QMessageBox.warning(self, "Theme Error", f"Failed to load theme: {str(e)}")

    def update_theme_button(self):
        """Update theme button appearance"""
        if self.current_theme == 'dark':
            self.theme_btn.setText('🌙')  # Moon emoji for dark theme
            self.theme_btn.setToolTip('Switch to Light Theme')
        else:
            self.theme_btn.setText('☀️')  # Sun emoji for light theme
            self.theme_btn.setToolTip('Switch to Dark Theme')

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
            # Update drop area style based on current theme
            if self.current_theme == 'dark':
                self.drop_area.setStyleSheet("""
                    QLabel {
                        border: 2px solid #00C853;
                        border-radius: 5px;
                        padding: 30px;
                        background: #1B5E20;
                        color: white;
                    }
                """)
            else:
                self.drop_area.setStyleSheet("""
                    QLabel {
                        border: 2px solid #4CAF50;
                        border-radius: 5px;
                        padding: 30px;
                        background: #E8F5E9;
                    }
                """)
        else:
            event.ignore()

    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Apply new settings
            self.apply_settings(dialog.settings)

    def apply_settings(self, settings):
        """Apply new settings to the application"""
        # Update logging
        if settings.enable_logging:
            import logging
            logging.getLogger().setLevel(getattr(logging, settings.log_level))
        
        # Update compression settings
        self.compression_manager.thread_pool.setMaxThreadCount(settings.max_threads)
        
        # Update FFmpeg parameters in compression function
        # This will be used when creating new compression tasks
        self.ffmpeg_settings = settings.ffmpeg

    def process_next_file(self):
        """Process the next file in the queue"""
        if self.current_file_index >= len(self.input_files):
            return

        input_path = self.input_files[self.current_file_index]
        
        # Get the executable's directory
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            exe_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Create output filename in the executable's directory
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(exe_dir, f"{base_name}_compressed.mp4")

        try:
            # Get compression settings
            preset_name = self.quality_preset_combo.currentText()
            if preset_name != 'Custom':
                preset_config = QUALITY_PRESETS[preset_name]
                preset = preset_config.preset
                crf = preset_config.crf
                resolution = preset_config.resolution
                bitrate = preset_config.bitrate
            else:
                preset = self.preset_combo.currentData()
                crf = self.crf_spin.value()
                resolution = self.get_resolution()
                bitrate = self.get_bitrate()

            # Update UI for compression start
            self.compress_btn.setEnabled(False)
            self.select_btn.setEnabled(False)
            self.progress_bar.setValue(0)
            self.progress_bar.setMaximum(100)

            # Update status
            self.status_label.setText(
                f"Processing file {self.current_file_index + 1} of {self.total_files}"
            )

            # Start compression in background thread
            self.worker = CompressionWorker(
                input_path, 
                output_path, 
                preset, 
                crf,
                resolution,
                bitrate
            )
            self.worker.progress.connect(self.update_progress)
            self.worker.percentage.connect(self.update_file_progress)
            self.worker.finished.connect(self.file_compression_finished)
            self.worker.start()

        except Exception as e:
            QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to process {os.path.basename(input_path)}: {str(e)}"
            )
            self.handle_compression_error()

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Video Compressor",
            """<h2>Video Compressor</h2>
            <p>Version 1.0</p>
            <p>Created by <b>Syed Bilal Alam</b></p>
            <p>A powerful video compression tool with advanced features.</p>
            <p>Copyright © 2024 Syed Bilal Alam. All rights reserved.</p>"""
        )

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = VideoCompressorUI()
    sys.exit(app.exec_()) 