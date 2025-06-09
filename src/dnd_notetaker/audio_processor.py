import argparse
import os
import shutil
import subprocess
import tempfile

from moviepy import VideoFileClip
from tqdm import tqdm

from .utils import setup_logging


class AudioProcessor:
    def __init__(self):
        self.logger = setup_logging("AudioProcessor")
        self.MAX_CHUNK_SIZE = 24 * 1024 * 1024  # 24MB to be safe
        self.temp_dirs = []  # Track temporary directories for cleanup

    def cleanup(self):
        """Clean up any temporary directories created"""
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    self.logger.debug(f"Cleaning up temporary directory: {temp_dir}")
                    shutil.rmtree(temp_dir)
            except Exception as e:
                self.logger.warning(
                    f"Failed to clean up directory {temp_dir}: {str(e)}"
                )

    def create_temp_dir(self):
        """Create a temporary directory and track it for cleanup"""
        temp_dir = tempfile.mkdtemp(prefix="audio_processor_")
        self.temp_dirs.append(temp_dir)
        return temp_dir

    def verify_audio_file(self, audio_path):
        """Verify audio file exists and is accessible"""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if not os.path.isfile(audio_path):
            raise ValueError(f"Path is not a file: {audio_path}")

        if not os.access(audio_path, os.R_OK):
            raise PermissionError(f"No permission to read file: {audio_path}")

    def extract_audio(self, video_path, output_dir):
        """Extract audio from video file"""
        self.logger.info(f"Extracting audio from video: {video_path}")

        try:
            # Verify input file
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")

            # Create output directory
            os.makedirs(output_dir, exist_ok=True)

            # Extract audio with progress bar
            video = VideoFileClip(video_path)
            duration = video.duration

            with tqdm(total=100, desc="Extracting audio") as pbar:

                def progress_callback(t):
                    pbar.update(int(t * 100) - pbar.n)

                audio_path = os.path.join(output_dir, "session_audio.mp3")
                video.audio.write_audiofile(
                    audio_path, logger=None
                )  # Disable moviepy's logging

            video.close()
            self.logger.info(f"Successfully extracted audio to: {audio_path}")
            return audio_path

        except Exception as e:
            self.logger.error(f"Error extracting audio: {str(e)}")
            raise

    def get_audio_duration(self, audio_path):
        """Get audio duration in seconds using ffprobe"""
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            self.logger.warning(f"Could not get duration with ffprobe: {str(e)}")
        return None

    def split_audio_with_ffmpeg(
        self, audio_path, output_dir, start_seconds, duration_seconds, chunk_num
    ):
        """Split audio using ffmpeg directly without loading into memory"""
        chunk_path = os.path.join(output_dir, f"chunk_{chunk_num}.mp3")
        cmd = [
            "ffmpeg",
            "-i",
            audio_path,
            "-ss",
            str(start_seconds),
            "-t",
            str(duration_seconds),
            "-acodec",
            "mp3",
            "-y",  # Overwrite output files
            chunk_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffmpeg failed: {result.stderr}")

        return chunk_path

    def split_audio(self, audio_path, output_dir):
        """
        Split audio file into chunks smaller than 25MB
        Returns list of paths to chunk files
        """
        self.logger.info(f"Processing audio file: {audio_path}")
        temp_dir = None

        try:
            # Verify input file
            self.verify_audio_file(audio_path)

            # Try to get file size first
            try:
                file_size = os.path.getsize(audio_path)
                self.logger.debug(f"Audio file size: {file_size/1024/1024:.1f}MB")

                # If file is small enough, return as is
                if file_size <= self.MAX_CHUNK_SIZE:
                    self.logger.info(
                        "Audio file is within size limit, no splitting needed"
                    )
                    return [audio_path]
            except Exception as e:
                self.logger.warning(
                    f"Could not determine file size, will attempt to split: {str(e)}"
                )

            # Create temporary directory for chunks
            temp_dir = self.create_temp_dir()

            # Get duration using ffprobe (doesn't load file into memory)
            duration_seconds = self.get_audio_duration(audio_path)
            if duration_seconds is None:
                self.logger.warning(
                    "Could not determine duration, attempting to split by file size estimate"
                )
                # Estimate based on typical MP3 bitrate (128 kbps)
                estimated_duration = (file_size * 8) / (128 * 1000)  # seconds
                duration_seconds = estimated_duration

            self.logger.debug(f"Audio duration: {duration_seconds/60:.1f} minutes")

            # Calculate chunks (15 minutes per chunk to be safe)
            chunk_duration_seconds = 15 * 60  # 15 minutes
            num_chunks = max(
                1,
                int(
                    (duration_seconds + chunk_duration_seconds - 1)
                    // chunk_duration_seconds
                ),
            )

            # If only one chunk needed, return original file
            if num_chunks == 1:
                self.logger.info("Audio duration suggests no splitting needed")
                return [audio_path]

            self.logger.info(f"Splitting into {num_chunks} chunks (~15 minutes each)")
            chunk_paths = []

            # Split using ffmpeg (memory efficient)
            with tqdm(total=num_chunks, desc="Splitting audio") as pbar:
                for i in range(num_chunks):
                    try:
                        start_time = i * chunk_duration_seconds
                        # Make sure we don't exceed the actual duration
                        chunk_duration = min(
                            chunk_duration_seconds, duration_seconds - start_time
                        )

                        chunk_path = self.split_audio_with_ffmpeg(
                            audio_path, temp_dir, start_time, chunk_duration, i + 1
                        )

                        # Verify chunk was created and check size
                        if os.path.exists(chunk_path):
                            chunk_size = os.path.getsize(chunk_path)
                            self.logger.debug(
                                f"Chunk {i+1} size: {chunk_size/1024/1024:.2f}MB"
                            )
                            chunk_paths.append(chunk_path)
                        else:
                            raise Exception(f"Failed to create chunk {i+1}")

                        pbar.update(1)

                    except Exception as e:
                        self.logger.error(f"Error processing chunk {i+1}: {str(e)}")
                        raise

            self.logger.info(f"Successfully split audio into {len(chunk_paths)} chunks")
            return chunk_paths

        except Exception as e:
            self.logger.error(f"Error splitting audio: {str(e)}")
            if temp_dir and os.path.exists(temp_dir):
                self.logger.debug("Cleaning up temporary files due to error")
                self.cleanup()
            raise


def main():
    """Main function for testing audio processor independently"""
    parser = argparse.ArgumentParser(description="Extract audio from video file")
    parser.add_argument(
        "--input", "-i", required=True, help="Path to the input video file"
    )
    parser.add_argument("--output", "-o", help="Output directory", default="output")
    parser.add_argument(
        "--keep-chunks", action="store_true", help="Keep temporary chunk files"
    )

    args = parser.parse_args()
    logger = setup_logging("AudioProcessorMain")

    processor = AudioProcessor()
    try:
        os.makedirs(args.output, exist_ok=True)

        # Extract audio
        logger.info("Extracting audio...")
        audio_path = processor.extract_audio(args.input, args.output)

        # Split audio if needed
        logger.info("Checking if splitting is needed...")
        chunk_paths = processor.split_audio(audio_path, args.output)

        if len(chunk_paths) > 1:
            logger.info(f"Audio split into {len(chunk_paths)} chunks:")
            for path in chunk_paths:
                logger.info(f"  - {path}")
        else:
            logger.info("No splitting needed")

    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise

    finally:
        if not args.keep_chunks:
            processor.cleanup()


if __name__ == "__main__":
    main()
