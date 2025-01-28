import json
import tempfile
import os
import argparse
from datetime import datetime
import openai
from tqdm import tqdm
from email_handler import EmailHandler
from audio_processor import AudioProcessor
from transcriber import Transcriber
from transcript_processor import FINAL_OUTPUT_PROCESSED_TRANSCRIPT, process_transcript
from docs_uploader import DocsUploader
from utils import load_config, setup_logging

class TranscriptProcessor:
    def __init__(self, openai_api_key):
        self.logger = setup_logging('TranscriptProcessor')
        self.openai_api_key = openai_api_key
    def process_transcript(self, directory, output_file):
        enhanced_narrative = process_transcript(directory=directory)
        # Save the narrative to a file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(enhanced_narrative)
        print(f"Narrative generation complete. Saved to {output_file}.")
        return None, output_file

class MeetingProcessor:
    def __init__(self, config_path=".credentials/config.json"):
        self.logger = setup_logging('MeetingProcessor')

        try:
            # Ensure .credentials directory exists
            os.makedirs(".credentials", exist_ok=True)

            # Load configuration
            self.logger.debug(f"Loading config from: {config_path}")
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Config file not found at: {config_path}")

            self.config = load_config(config_path)
            if self.config["openai_api_key"]:
                os.environ["OPENAI_API_KEY"] = self.config["openai_api_key"]

            # Initialize components
            self.email_handler = EmailHandler(self.config["email"])
            self.transcriber = Transcriber(self.config["openai_api_key"])
            self.transcript_processor = TranscriptProcessor(self.config["openai_api_key"])
            self.docs_uploader = DocsUploader()

            self.logger.debug("All components initialized successfully")

        except Exception as e:
            self.logger.error(f"Error initializing MeetingProcessor: {str(e)}")
            raise

    def get_output_dir_from_filename(self, filename):
        """
        Extract meeting name and date from filename to create output directory name
        Example: "DnD - 2025-01-10 18-41 CST - Recording" -> "output/dnd_sessions_2025_01_10"
        """
        try:
            # Split filename into components
            parts = filename.split(" - ")
            if len(parts) >= 2:
                # Extract meeting name (e.g., "DnD")
                meeting_name = parts[0].strip().lower().replace(" ", "_")

                # Extract date (e.g., "2025-01-10")
                date_str = parts[1].strip().split()[0]  # Get just the date part

                # Convert date format (replace hyphens with underscores)
                formatted_date = date_str.replace("-", "_")

                # Combine into directory name
                dir_name = f"{meeting_name}_sessions_{formatted_date}"

                # Return full path under 'output' directory
                return os.path.join("output", dir_name)

            # Fallback if parsing fails
            self.logger.warning(f"Could not parse directory name from filename: {filename}")
            return os.path.join("output", "session_default")

        except Exception as e:
            self.logger.error(f"Error parsing filename for output directory: {str(e)}")
            return os.path.join("output", "session_default")

    def process_meeting(self, email_subject_filter: str = "Meeting records", output_dir: str = "output"):
        """Process meeting recording end-to-end"""
        self.logger.info("Starting meeting processing")
        try:
            # Verify/create output directory
            os.makedirs(output_dir, exist_ok=True)

            # First download the recording to get its name
            self.logger.info("Downloading meeting recording...")
            video_path = self.email_handler.download_meet_recording(
                email_subject_filter, 
                output_dir
            )       
            # Extract audio
            self.logger.info("Extracting audio...")

            processor = AudioProcessor()
            audio_path = processor.extract_audio(video_path)
            self.logger.info(f"Extracted audio to: {audio_path}")
            # Split audio if needed
            self.logger.info("Checking if splitting is needed...")
            chunk_paths = processor.split_audio(audio_path)
            # Generate transcript
            transcript_paths = []
            chunk_paths.sort()
            for i, chunk_path in enumerate(chunk_paths):
                print(f"Processing chunk {i+1} of {len(chunk_paths)} from {chunk_path}")
                # get filename from chunk_path without extension
                chunk_filename = os.path.splitext(os.path.basename(chunk_path))[0]
                transcript_filename = os.path.join(output_dir, "transcripts", chunk_filename + ".txt")
                # if file exists continue
                if os.path.exists(transcript_filename):
                    transcript_paths.append(transcript_filename)
                    continue
                else:
                    # make sure the directory exists
                    os.makedirs(os.path.dirname(transcript_filename), exist_ok=True)
                # accumates a combined transcript of all chunks
                self.logger.info(f"Creating chunk transcript: {transcript_filename}")
                transcript, transcript_path = self.transcriber.get_transcript(
                    chunk_path,
                    transcript_filename
                )
                transcript_paths.append(transcript_path)
                self.logger.info("Transcript generated successfully: {transcript_path}")
            # Process transcript
            # Sort the transcript paths to ensure correct order
            transcript_paths.sort()
            # Create processed transcript filename based on output directory
            _, notes_path = self.transcript_processor.process_transcript(
                directory=os.path.dirname(transcript_paths[0]),
                output_file=FINAL_OUTPUT_PROCESSED_TRANSCRIPT
            )
            self.logger.info("Transcript processed successfully")

            # Save processing summary
            outputs = {
                "video_path": video_path,
                "process_transcript_path": notes_path,
            }
            return outputs

        except Exception as e:
            self.logger.error(f"Error in process_meeting: {str(e)}")
            raise


def main():
    """Main function for running the complete pipeline"""
    logger = setup_logging('MainScript')

    parser = argparse.ArgumentParser(description='Process DnD session recordings')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Process command
    process_parser = subparsers.add_parser('process', help='Process a session recording')
    process_parser.add_argument('--output', '-o', help='Output directory (defaults to directory based on meeting name and date)', default='output')
    process_parser.add_argument('--config', help='Path to config file', default='.credentials/config.json')
    process_parser.add_argument('--subject', '-s', help='Email subject filter', default="Meeting records")

    args = parser.parse_args()
    logger.debug(f"Arguments parsed: {args}")

    try:
        if args.command == 'process':
            # Initialize processor
            processor = MeetingProcessor(args.config)

            # Process meeting
            logger.info("Starting meeting processing pipeline...")
            results = processor.process_meeting(
                email_subject_filter=args.subject,
                output_dir=args.output,
            )

            # Print summary of outputs
            print("\nProcessing Summary:")
            for key, value in results.items():
                print(f"{key}: {value}")

        else:
            parser.print_help()

    except Exception as e:
        logger.error(f"Operation failed: {str(e)}\nArgs: {args}")
        raise

if __name__ == "__main__":
    main()