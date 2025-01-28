from moviepy.editor import VideoFileClip
import os
import argparse
from pydub import AudioSegment
from utils import setup_logging
from tqdm import tqdm
import shutil
import tempfile

class AudioProcessor:
    def __init__(self, output_dir="output"):
        self.logger = setup_logging('AudioProcessor')
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
                self.logger.warning(f"Failed to clean up directory {temp_dir}: {str(e)}")

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

    def extract_audio(self, video_path) -> str:
        """Extract audio from video file"""
        self.logger.info(f"Extracting audio from video: {video_path}")
        # Create audiofile path from video file
        output_file = os.path.splitext(video_path)[0] + ".mp3"
        try:
            # Verify input file
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            # Create output directory
            if os.path.exists(output_file):
                self.logger.warning(f"Audio file already exists: {output_file}")
                return output_file 
            # Extract audio with progress bar
            video = VideoFileClip(video_path)
            video.audio.write_audiofile(output_file, logger=None)
            video.close()
            self.logger.info(f"Successfully extracted audio to: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Error extracting audio: {str(e)}")
            raise

    def split_audio(self, audio_path):
        """
        Split audio file into chunks smaller than 25MB
        Returns list of paths to chunk files
        """
        self.logger.info(f"Splitting audio file: {audio_path}")
        temp_dir = "output/audio_chunks"
        
        try:
            # check if chucks already exist
            if os.path.exists(temp_dir):
                return [os.path.join(temp_dir, file) for file in os.listdir(temp_dir)]
            
            # Verify input file
            self.verify_audio_file(audio_path)
            
            # # Create temporary directory for chunks
            # temp_dir = self.create_temp_dir()
            os.makedirs(temp_dir, exist_ok=True)

            # Load audio file
            self.logger.debug("Loading audio file...")
            audio = AudioSegment.from_mp3(audio_path)
            duration_ms = len(audio)
            
            # Calculate chunk size based on file size
            file_size = os.path.getsize(audio_path)
            if file_size <= self.MAX_CHUNK_SIZE:
                self.logger.info("Audio file small enough, no splitting needed")
                return [audio_path]
            
            # Calculate how many chunks we need
            num_chunks = (file_size // self.MAX_CHUNK_SIZE) + 1
            chunk_duration = duration_ms // num_chunks
            
            self.logger.info(f"Splitting into {num_chunks} chunks")
            chunk_paths = []
            
            # Split and export chunks with progress bar
            with tqdm(total=num_chunks, desc="Splitting audio") as pbar:
                for i in range(num_chunks):
                    try:
                        start_time = i * chunk_duration
                        end_time = min((i + 1) * chunk_duration, duration_ms)
                        
                        chunk = audio[start_time:end_time]
                        chunk_path = os.path.join(temp_dir, f'chunk_{i+1}.mp3')
                        
                        # Export chunk
                        chunk.export(chunk_path, format='mp3')
                        
                        # Verify chunk size
                        chunk_size = os.path.getsize(chunk_path)
                        if chunk_size > self.MAX_CHUNK_SIZE:
                            raise ValueError(f"Chunk {i+1} exceeds size limit: {chunk_size/1024/1024:.2f}MB")
                        
                        self.logger.debug(f"Chunk {i+1} size: {chunk_size/1024/1024:.2f}MB")
                        chunk_paths.append(chunk_path)
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

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Extract and process audio from video files')
    parser.add_argument('--input', '-i', required=True, help='Path to the input video file')
    parser.add_argument('--output', '-o', help='Output directory', default='output')
    parser.add_argument('--keep-chunks', action='store_true', help='Keep temporary chunk files')
    return parser.parse_args()

def main(input_path: str, output_dir: str, keep_chunks: bool) -> str:
    """Main function with typed inputs"""
    logger = setup_logging('AudioProcessorMain')
    processor = AudioProcessor()
    try:
        os.makedirs(output_dir, exist_ok=True)

        # Extract audio
        logger.info("Extracting audio...")
        audio_path = processor.extract_audio(input_path, output_dir)

        # Split audio if needed
        logger.info("Checking if splitting is needed...")
        chunk_paths = processor.split_audio(audio_path, output_dir)

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
        if not keep_chunks:
            processor.cleanup()
    return audio_path

if __name__ == "__main__":
    args = parse_args()
    main(args.input, args.output, args.keep_chunks)