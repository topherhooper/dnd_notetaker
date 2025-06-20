import argparse
import json
import logging
import os

import openai
from tqdm import tqdm

from .audio_processor import AudioProcessor
from .utils import save_text_output, setup_logging
from .config import Config


class Transcriber:
    def __init__(self, api_key, config: Config):
        self.logger = setup_logging("Transcriber")
        self.config = config
        if not config or not config.dry_run:
            self.client = openai.OpenAI(api_key=api_key)
        else:
            self.client = None
        self.model = "gpt-4o-transcribe"
        self.output_dir = config.output_dir

    def get_transcript(self, audio_path):
        """
        Generate transcript using OpenAI's Whisper API

        Args:
            audio_path (str): Path to the audio file
            output_dir (str, optional): Directory to save the transcript

        Returns:
            tuple: (transcript text, path to saved file if output_dir provided)
        """
        self.logger.info(f"Generating transcript for audio: {audio_path}")

        try:
            # Verify audio file exists
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # Always use AudioProcessor to split the file (it will handle single chunks)
            self.logger.info("Preparing audio for transcription...")
            audio_processor = AudioProcessor()
            chunk_paths = audio_processor.split_audio(
                audio_path, self.output_dir or os.path.dirname(audio_path)
            )

            # Transcribe each chunk
            transcripts = []
            if len(chunk_paths) == 1:
                self.logger.info("Processing single audio file...")
            else:
                self.logger.info(f"Processing {len(chunk_paths)} audio chunks...")

            with tqdm(total=len(chunk_paths), desc="Transcribing") as pbar:
                for i, chunk_path in enumerate(chunk_paths):
                    if len(chunk_paths) > 1:
                        self.logger.debug(
                            f"Transcribing chunk {i+1}/{len(chunk_paths)}"
                        )
                    with open(chunk_path, "rb") as audio_file:
                        chunk_transcript = self.client.audio.transcriptions.create(
                            model="whisper-1", file=audio_file, response_format="text"
                        )
                    transcripts.append(chunk_transcript)
                    pbar.update(1)

            # Clean up chunks (only if they were created)
            if len(chunk_paths) > 1 or chunk_paths[0] != audio_path:
                audio_processor.cleanup()

            # Combine transcripts
            transcript = "\n\n".join(transcripts)
            self.logger.info(f"Successfully generated transcript")
            self.logger.debug(f"Total transcript length: {len(transcript)} characters")

            # Save transcript if output directory provided
            filepath = save_text_output(transcript, "full_transcript", output_dir)
            return transcript, filepath

            return transcript, None

        except Exception as e:
            self.logger.error(f"Error generating transcript: {str(e)}")
            raise
    
    def transcribe(self, audio_path):
        """
        Simplified transcribe method for MeetProcessor
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            str: Transcript text
        """
        if self.config and self.config.dry_run:
            # Dry run mode - just show what would happen
            print(f"[DRY RUN] Would transcribe audio using OpenAI Whisper:")
            print(f"  Audio file: {audio_path}")
            print(f"  Model: whisper-1")
            print(f"  Estimated cost: ~$0.006 per minute")
            return "[DRY RUN - No actual transcript]"
            
        transcript, _ = self.get_transcript(str(audio_path))
        return transcript


