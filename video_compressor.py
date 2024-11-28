import subprocess
import os
import time
import logging
from typing import Optional, Tuple, Callable
from enum import Enum
from datetime import datetime, timedelta
import re
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('compression.log'),
        logging.StreamHandler()
    ]
)

class VideoPreset(Enum):
    FAST = "ultrafast"
    BALANCED = "medium"
    BEST = "veryslow"

class CompressionStats:
    def __init__(self):
        self.start_time = time.time()
        self.frame_count = 0
        self.duration = 0
        self.processed_frames = 0
        self.processed_duration = 0
        self.current_fps = 0
        self.average_fps = 0
        self.estimated_time = 0
        self.file_size = 0
        self.current_size = 0

def get_video_info(input_path: str) -> dict:
    """Get video information using FFprobe"""
    try:
        # Get video duration and frame count
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration,nb_frames',
            '-show_entries', 'format=duration,size',
            '-of', 'json',
            input_path
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"FFprobe error: {result.stderr}")

        import json
        info = json.loads(result.stdout)
        
        # Extract relevant information
        stream_info = info.get('streams', [{}])[0]
        format_info = info.get('format', {})
        
        return {
            'width': int(stream_info.get('width', 0)),
            'height': int(stream_info.get('height', 0)),
            'duration': float(format_info.get('duration', 0)),
            'frame_count': int(stream_info.get('nb_frames', 0)),
            'file_size': int(format_info.get('size', 0))
        }
    except Exception as e:
        logging.error(f"Error getting video info: {str(e)}")
        return {}

def parse_ffmpeg_progress(line: str, stats: CompressionStats) -> dict:
    """Parse FFmpeg progress output"""
    progress = {}
    
    try:
        # Extract time information
        time_match = re.search(r'time=(\d+):(\d+):(\d+.\d+)', line)
        if time_match:
            hours, minutes, seconds = map(float, time_match.groups())
            stats.processed_duration = hours * 3600 + minutes * 60 + seconds
            
            # Calculate progress percentage
            if stats.duration > 0:
                progress['percentage'] = min(
                    100, (stats.processed_duration / stats.duration) * 100
                )

        # Extract frame information
        frame_match = re.search(r'frame=\s*(\d+)', line)
        if frame_match:
            stats.processed_frames = int(frame_match.group(1))
            
            # Calculate FPS and time estimates
            elapsed_time = time.time() - stats.start_time
            if elapsed_time > 0:
                stats.current_fps = stats.processed_frames / elapsed_time
                if stats.frame_count > 0:
                    remaining_frames = stats.frame_count - stats.processed_frames
                    stats.estimated_time = remaining_frames / stats.current_fps

        # Extract size information
        size_match = re.search(r'size=\s*(\d+)kB', line)
        if size_match:
            stats.current_size = int(size_match.group(1)) * 1024

        # Update progress dictionary
        progress.update({
            'frame': stats.processed_frames,
            'fps': stats.current_fps,
            'size': stats.current_size,
            'time': stats.processed_duration,
            'estimated_time': stats.estimated_time
        })

    except Exception as e:
        logging.error(f"Error parsing FFmpeg progress: {str(e)}")

    return progress

def compress_video(
    input_path: str,
    output_path: str,
    resolution: Optional[Tuple[int, int]] = None,
    bitrate: Optional[str] = None,
    preset: VideoPreset = VideoPreset.BALANCED,
    crf: int = 23,
    progress_callback: Optional[Callable] = None,
    temp_dir: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Compress a video using FFmpeg with enhanced error handling and progress monitoring.
    """
    stats = CompressionStats()
    temp_output = None
    
    try:
        # Create temp directory if needed
        if temp_dir:
            os.makedirs(temp_dir, exist_ok=True)
            temp_output = os.path.join(temp_dir, f"temp_{os.path.basename(output_path)}")
        
        # Get video information
        logging.info(f"Analyzing video: {input_path}")
        video_info = get_video_info(input_path)
        if not video_info:
            return False, "Failed to get video information"
        
        stats.duration = video_info['duration']
        stats.frame_count = video_info['frame_count']
        stats.file_size = video_info['file_size']
        
        # Verify input file exists and is accessible
        if not os.path.exists(input_path):
            return False, f"Input file not found: {input_path}"
        
        if not os.access(input_path, os.R_OK):
            return False, f"Input file is not readable: {input_path}"

        # Build FFmpeg command
        command = ['ffmpeg', '-i', input_path]

        # Add video codec and settings
        command.extend(['-c:v', 'libx264'])
        command.extend(['-preset', preset.value])
        command.extend(['-crf', str(crf)])

        # Add resolution if specified
        if resolution:
            width, height = resolution
            command.extend(['-vf', f'scale={width}:{height}'])

        # Add bitrate if specified
        if bitrate:
            command.extend(['-b:v', bitrate])

        # Add audio settings
        command.extend(['-c:a', 'aac'])

        # Add output path (use temp file if specified)
        target_path = temp_output if temp_output else output_path
        command.extend(['-y', target_path])

        logging.info(f"Starting compression with command: {' '.join(command)}")
        stats.start_time = time.time()

        # Run FFmpeg command with progress monitoring
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # Monitor the FFmpeg output
        while True:
            if process.stderr:
                output = process.stderr.readline()
                
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    # Log FFmpeg output
                    logging.debug(output.strip())
                    
                    # Parse progress
                    progress = parse_ffmpeg_progress(output, stats)
                    
                    if progress and progress_callback:
                        # Format estimated time
                        eta = timedelta(seconds=int(stats.estimated_time))
                        size_mb = stats.current_size / (1024 * 1024)
                        
                        # Create progress message
                        progress_msg = (
                            f"Progress: {progress.get('percentage', 0):.1f}% "
                            f"[{stats.processed_frames}/{stats.frame_count} frames] "
                            f"FPS: {stats.current_fps:.1f} "
                            f"Size: {size_mb:.1f}MB "
                            f"ETA: {eta}"
                        )
                        
                        progress_callback(progress_msg)

        returncode = process.poll()

        if returncode != 0:
            error_output = process.stderr.read() if process.stderr else "Unknown error"
            logging.error(f"FFmpeg error: {error_output}")
            return False, f"Compression failed: {error_output}"

        # Move temp file to final destination if used
        if temp_output and os.path.exists(temp_output):
            shutil.move(temp_output, output_path)

        # Verify output file was created
        if not os.path.exists(output_path):
            return False, "Output file was not created"

        # Calculate compression results
        input_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
        output_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        reduction = ((input_size - output_size) / input_size) * 100
        
        compression_time = time.time() - stats.start_time
        average_fps = stats.frame_count / compression_time if compression_time > 0 else 0

        result_message = (
            f"Compression successful!\n"
            f"Size reduced by {reduction:.1f}%\n"
            f"Original: {input_size:.1f}MB → Compressed: {output_size:.1f}MB\n"
            f"Time taken: {timedelta(seconds=int(compression_time))}\n"
            f"Average FPS: {average_fps:.1f}"
        )
        
        logging.info(result_message)
        return True, result_message

    except Exception as e:
        error_message = f"Error during compression: {str(e)}"
        logging.error(error_message, exc_info=True)
        
        # Clean up temp file if it exists
        if temp_output and os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except:
                pass
                
        return False, error_message

if __name__ == "__main__":
    def print_progress(msg):
        print(msg, end='\r')

    success, message = compress_video(
        input_path="input.mp4",
        output_path="output.mp4",
        progress_callback=print_progress
    )
    print(f"\n{message}") 