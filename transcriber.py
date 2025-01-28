from typing import Tuple
import openai
import json
from pydub import AudioSegment
import argparse
import os
from utils import setup_logging, save_text_output

class Transcriber:
    def __init__(self, api_key):
        self.logger = setup_logging('Transcriber')
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4o"

    def get_transcript(self, audio_path, output_path) -> Tuple[str, str]:
        """
        Generate transcript using OpenAI's Whisper API
        
        Args:
            audio_path (str): Path to the audio file
            output_dir (str, optional): Directory to save the transcript
            
        Returns:
            tuple: (transcript text, path to saved file if output_dir provided)
        """
        # if file already exists, return the content
        if os.path.exists(output_path):
            with open(output_path, 'r') as f:
                return f.read(), output_path
        self.logger.info(f"Generating transcript for audio: {audio_path}")
        
        try:
            # Verify transcript file exists
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            max_size = 25 * 1024 * 1024  # 25MB in bytes

            # Check if file exceeds size limit
            if os.path.getsize(audio_path) > max_size:
                # Create a compressed version
                compressed_path = "compressed_audio.mp3"
                audio = AudioSegment.from_file(audio_path)
                
                # Compress to 64kbps MP3 (adjust bitrate as needed)
                audio.export(compressed_path, format="mp3", bitrate="64k")
                
                # Verify compressed file size
                if os.path.getsize(compressed_path) > max_size:
                    raise ValueError("Compressed file still exceeds size limit")
                
                audio_path = compressed_path  # Use compressed file
            
            # Generate transcript using Whisper
            with open(audio_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            self.logger.info("Successfully generated transcript")
            self.logger.debug(f"Transcript length: {len(transcript)} characters")
            
            # Save transcript if output directory provided
            if output_path:
                filepath = save_text_output(transcript, output_path)
                self.logger.info(f"Transcript saved to: {filepath}")
                return transcript, filepath
            
            return transcript, None
            
        except Exception as e:
            self.logger.error(f"Error generating transcript: {str(e)}")
            raise

def main():
    """Main function for testing transcriber independently"""
    logger = setup_logging('TranscriberMain')
    
    parser = argparse.ArgumentParser(description='Transcribe audio file')
    parser.add_argument('--input', '-i', required=True, help='Path to the input audio file')
    parser.add_argument('--output', '-o', help='Output directory', default='output')
    parser.add_argument('--config', help='Path to config file', default='.credentials/config.json')
    
    args = parser.parse_args()
    logger.debug(f"Arguments parsed: {args}")
    
    try:
        # Load config for API key
        with open(args.config, 'r') as f:
            config = json.load(f)
        logger.debug("Config loaded successfully")
        
        transcriber = Transcriber(config['openai_api_key'])
        transcript, filepath = transcriber.get_transcript(args.input, args.output)
        
        if filepath:
            logger.info(f"Transcript saved to: {filepath}")
        else:
            logger.info("Transcript result:")
            print(transcript)
            
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()