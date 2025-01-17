from moviepy.editor import VideoFileClip
import os
import argparse
from pydub import AudioSegment
from utils import setup_logging
from tqdm import tqdm
import shutil
import tempfile

class AudioProcessor:
    def __init__(self):
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
                
                audio_path = os.path.join(output_dir, 'audio.mp3')
                video.audio.write_audiofile(audio_path, 
                                         logger=None,  # Disable moviepy's logging
                                         progress_callback=progress_callback)
            
            video.close()
            self.logger.info(f"Successfully extracted audio to: {audio_path}")
            return audio_path
            
        except Exception as e:
            self.logger.error(f"Error extracting audio: {str(e)}")
            raise

    def split_audio(self, audio_path, output_dir):
        """
        Split audio file into chunks smaller than 25MB
        Returns list of paths to chunk files
        """
        self.logger.info(f"Splitting audio file: {audio_path}")
        temp_dir = None
        
        try:
            # Verify input file
            self.verify_audio_file(audio_path)
            
            # Create temporary directory for chunks
            temp_dir = self.create_temp_dir()
            
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

def main():
    """Main function for testing audio processor independently"""
    parser = argparse.ArgumentParser(description='Extract audio from video file')
    parser.add_argument('--input', '-i', required=True, help='Path to the input video file')
    parser.add_argument('--output', '-o', help='Output directory', default='output')
    parser.add_argument('--keep-chunks', action='store_true', help='Keep temporary chunk files')
    
    args = parser.parse_args()
    logger = setup_logging('AudioProcessorMain')
    
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