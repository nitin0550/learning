import os
import subprocess
import shutil
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple
from pathlib import Path
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import re
from google.cloud import storage
from django.core.files.storage import default_storage



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoConversionError(Exception):
    """Custom exception for video conversion errors"""
    pass

def validate_inputs(video_path: str, output_dir: str) -> None:
    """Validate input parameters"""
    if not os.path.exists(video_path):
        raise ValueError(f"Video file not found: {video_path}")
    if not video_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
        raise ValueError("Unsupported video format")

def get_bitrate_for_resolution(resolution: str) -> int:
    """Return appropriate bitrate for resolution"""
    bitrates = {
        '640x360': 800_000,    # 800Kbps
        '854x480': 1_400_000,  # 1.4Mbps
        '1280x720': 2_800_000, # 2.8Mbps
        '1920x1080': 5_000_000 # 5Mbps
    }
    return bitrates.get(resolution, 800_000)

def cleanup_temp_files(directory: str) -> None:
    """Clean up temporary files"""
    try:
        for filename in os.listdir(directory):
            if filename.endswith('.ts'):
                os.remove(os.path.join(directory, filename))
    except Exception as e:
        logger.warning(f"Error during cleanup: {e}")

def upload_to_gcs(bucket_name: str, source_file_name: str, destination_blob_name: str) -> None:
    """Uploads a file to Google Cloud Storage"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    logger.info(f"File {source_file_name} uploaded to {destination_blob_name}.")


def get_hls_directory(user_id: str, course_id: str, lesson_id: str) -> str:
    """Generate HLS directory path"""
    return os.path.join(settings.MEDIA_ROOT, 'expert', user_id, 'courses', course_id, 'hls', str(lesson_id))

def convert_to_hls(video_path: str, output_dir: str, user_id: str, course_id: str, lesson_id: str) -> str:
    """Convert video to HLS format with multiple resolutions"""
    try:
        validate_inputs(video_path, output_dir)
        
        # Create full HLS directory path
        hls_dir = get_hls_directory(user_id, course_id, lesson_id)
        os.makedirs(hls_dir, exist_ok=True)
        
        resolutions = ['640x360', '854x480', '1280x720', '1920x1080']
        playlists: List[Tuple[str, str]] = []

        def convert_resolution(resolution: str) -> Tuple[str, str]:
            resolution_name = resolution.replace('x', '_')
            output_name = f'index_{resolution_name}'
            hls_playlist = os.path.join(hls_dir, f'{output_name}.m3u8')
            
            bitrate = get_bitrate_for_resolution(resolution)
            segment_time = 10  # Shorter segments for better loading

            command = [
                'ffmpeg', '-i', video_path,
                '-s', resolution,
                '-c:v', 'libx264',
                '-b:v', str(bitrate),
                '-maxrate', str(int(bitrate * 1.2)),
                '-bufsize', str(int(bitrate * 2)),
                '-preset', 'ultrafast',
                '-profile:v', 'baseline',
                '-hls_time', str(segment_time),
                '-hls_list_size', '0',
                '-hls_segment_filename', os.path.join(hls_dir, f'{output_name}_%03d.ts'),
                '-f', 'hls',
                hls_playlist
            ]

            try:
                #subprocess.run(command, check=True, capture_output=True, text=True)

                
                subprocess.run(command, check=True, capture_output=True, text=True)
                # Upload each segment and playlist file to Google Cloud Storage
                bucket_name = settings.GS_BUCKET_NAME
                for filename in os.listdir(output_dir):
                    if filename.startswith(output_name):
                        file_path = os.path.join(output_dir, filename)
                        destination_blob_name = f'expert/{user_id}/courses/{course_id}/hls/{lesson_id}/{filename}'
                        upload_to_gcs(bucket_name, file_path, destination_blob_name)



                return resolution, os.path.basename(hls_playlist)
            
            except subprocess.CalledProcessError as e:
                logger.error(f"FFMPEG error: {e.stderr}")
                raise VideoConversionError(f"Failed to convert {resolution}: {e.stderr}")

        # Convert all resolutions
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(convert_resolution, res) for res in resolutions]
            for future in futures:
                try:
                    resolution, playlist = future.result()
                    playlists.append((resolution, playlist))
                except Exception as e:
                    logger.error(f"Resolution conversion failed: {e}")

        # Create master playlist
        master_playlist_path = os.path.join(hls_dir, 'index.m3u8')
        with open(master_playlist_path, 'w') as master:
            master.write('#EXTM3U\n')
            for resolution, playlist in playlists:
                bitrate = get_bitrate_for_resolution(resolution)
                master.write(f'#EXT-X-STREAM-INF:BANDWIDTH={bitrate},RESOLUTION={resolution}\n')
                master.write(f'{playlist}\n')

        # Upload files to Google Cloud Storage
        bucket_name = settings.GS_BUCKET_NAME
        destination_blob_name = f'expert/{user_id}/courses/{course_id}/hls/{lesson_id}/index.m3u8'
        upload_to_gcs(bucket_name, master_playlist_path, destination_blob_name)


        logger.info(f"HLS conversion complete: {master_playlist_path}")
        return f'https://storage.googleapis.com/{bucket_name}/expert/{user_id}/courses/{course_id}/hls/{lesson_id}/index.m3u8'
        #return os.path.relpath(master_playlist_path, settings.MEDIA_ROOT)

    except Exception as e:
        logger.error(f"Video conversion failed: {e}")
        raise VideoConversionError(f"Failed to convert video: {str(e)}")

def get_duration(filename):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
           '-of', 'default=noprint_wrappers=1:nokey=1', filename]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return float(result.stdout)


def track_progress(process, duration, user_id):
    channel_layer = get_channel_layer()
    pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.\d{2}")
    
    while True:
        line = process.stderr.readline().decode()
        if not line:
            break
            
        match = pattern.search(line)
        if match:
            h, m, s = map(int, match.groups())
            time_processed = h * 3600 + m * 60 + s
            progress = (time_processed / float(duration)) * 100
            
            # Send progress via WebSocket
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                {
                    "type": "upload_progress",
                    "progress": round(progress, 2)
                }
            )