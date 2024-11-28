class CompressionWorker(QThread):
    progress = pyqtSignal(str)
    percentage = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, input_path, output_path, preset, crf, resolution=None, bitrate=None):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.preset = preset
        self.crf = crf
        self.resolution = resolution
        self.bitrate = bitrate
        self.process = None

    def run(self):
        try:
            # Build FFmpeg command
            command = ['ffmpeg', '-i', self.input_path, '-y']  # -y to overwrite output

            # Add video codec settings
            command.extend(['-c:v', 'libx264'])
            command.extend(['-preset', self.preset.value])
            command.extend(['-crf', str(self.crf)])

            # Add resolution if specified
            if self.resolution:
                width, height = self.resolution
                command.extend(['-vf', f'scale={width}:{height}'])

            # Add bitrate if specified
            if self.bitrate:
                command.extend(['-b:v', self.bitrate])

            # Add audio settings
            command.extend(['-c:a', 'aac'])

            # Add output path
            command.append(self.output_path)

            # Start FFmpeg process
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW  # Hide console window on Windows
            )

            # Monitor progress
            while True:
                if self.process.poll() is not None:
                    break
                
                line = self.process.stderr.readline()
                if line:
                    self.progress.emit(line.strip())
                    # Parse progress and emit percentage
                    if 'time=' in line:
                        try:
                            time_str = line.split('time=')[1].split()[0]
                            h, m, s = map(float, time_str.split(':'))
                            current_time = h * 3600 + m * 60 + s
                            
                            # Get video duration if not already known
                            if not hasattr(self, 'duration'):
                                probe = subprocess.run(
                                    ['ffprobe', '-v', 'error', '-show_entries', 
                                     'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', 
                                     self.input_path],
                                    capture_output=True,
                                    text=True
                                )
                                self.duration = float(probe.stdout)
                            
                            # Calculate and emit progress percentage
                            if self.duration > 0:
                                percentage = min(int((current_time / self.duration) * 100), 100)
                                self.percentage.emit(percentage)
                        except:
                            pass

            # Check if compression was successful
            if self.process.returncode == 0:
                self.finished.emit(True, "Compression completed successfully!")
            else:
                error_output = self.process.stderr.read()
                self.finished.emit(False, f"Compression failed: {error_output}")

        except Exception as e:
            self.finished.emit(False, f"Error during compression: {str(e)}")

    def stop(self):
        """Stop the compression process"""
        if self.process:
            self.process.terminate() 