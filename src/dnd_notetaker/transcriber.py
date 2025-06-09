import argparse
import json
import logging
import os

import openai
from tqdm import tqdm

from .audio_processor import AudioProcessor
from .utils import save_text_output, setup_logging


class Transcriber:
    def __init__(self, api_key):
        self.logger = setup_logging("Transcriber")
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4o"

    def get_transcript(self, audio_path, output_dir=None):
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
                audio_path, output_dir or os.path.dirname(audio_path)
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
            if output_dir:
                filepath = save_text_output(transcript, "full_transcript", output_dir)
                return transcript, filepath

            return transcript, None

        except Exception as e:
            self.logger.error(f"Error generating transcript: {str(e)}")
            raise


def main():
    """Main function for testing transcriber independently"""
    logger = setup_logging("TranscriberMain")

    parser = argparse.ArgumentParser(description="Transcribe audio file")
    parser.add_argument(
        "--input", "-i", required=True, help="Path to the input audio file"
    )
    parser.add_argument("--output", "-o", help="Output directory", default="output")
    parser.add_argument(
        "--config", help="Path to config file", default=".credentials/config.json"
    )

    args = parser.parse_args()
    logger.debug(f"Arguments parsed: {args}")

    try:
        # Load config for API key
        with open(args.config, "r") as f:
            config = json.load(f)
        logger.debug("Config loaded successfully")

        transcriber = Transcriber(config["openai_api_key"])
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
