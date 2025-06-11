import argparse
import json
import os
import re
import shutil
from datetime import datetime

from tqdm import tqdm

from .audio_processor import AudioProcessor
from .docs_uploader import DocsUploader
from .drive_handler import DriveHandler
from .transcriber import Transcriber
from .transcript_processor import TranscriptProcessor
from .utils import cleanup_old_temp_directories, list_temp_directories, setup_logging


class MeetingProcessor:
    def __init__(self, config_path=".credentials/config.json"):
        self.logger = setup_logging("MeetingProcessor")

        try:
            # Ensure .credentials directory exists
            os.makedirs(".credentials", exist_ok=True)

            # Load configuration
            self.logger.debug(f"Loading config from: {config_path}")
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Config file not found at: {config_path}")

            with open(config_path, "r") as f:
                self.config = json.load(f)

            # Initialize components
            self.drive_handler = DriveHandler()
            self.audio_processor = AudioProcessor()
            self.transcriber = Transcriber(self.config["openai_api_key"])
            self.transcript_processor = TranscriptProcessor(
                self.config["openai_api_key"]
            )
            self.docs_uploader = DocsUploader()

            self.logger.debug("All components initialized successfully")

        except Exception as e:
            self.logger.error(f"Error initializing MeetingProcessor: {str(e)}")
            raise

    def verify_output_directory(self, output_dir):
        """Verify output directory exists and is writable"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            test_file = os.path.join(output_dir, ".write_test")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                return True
            except Exception as e:
                self.logger.error(f"Output directory is not writable: {str(e)}")
                raise
        except Exception as e:
            self.logger.error(f"Error verifying output directory: {str(e)}")
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
                meeting_name = parts[0].strip().lower()
                # Replace spaces and special characters with underscores
                meeting_name = re.sub(r'[^a-z0-9]+', '_', meeting_name)
                # Remove leading/trailing underscores
                meeting_name = meeting_name.strip('_')

                # Extract date (e.g., "2025-01-10")
                date_str = parts[1].strip().split()[0]  # Get just the date part

                # Convert date format (replace hyphens, slashes, and dots with underscores)
                formatted_date = date_str.replace("-", "_").replace("/", "_").replace(".", "_")

                # Combine into directory name
                dir_name = f"{meeting_name}_sessions_{formatted_date}"

                # Return full path under 'output' directory
                return os.path.join("output", dir_name)

            # Fallback if parsing fails
            self.logger.warning(
                f"Could not parse directory name from filename: {filename}"
            )
            return os.path.join("output", "session_default")

        except Exception as e:
            self.logger.error(f"Error parsing filename for output directory: {str(e)}")
            return os.path.join("output", "session_default")

    def check_already_processed(self, output_dir):
        """Check if this session has already been processed"""
        if not os.path.exists(output_dir):
            return False

        # Check for key output files
        expected_files = [
            "processed_notes.txt",
            "full_transcript.txt",
            "session_audio.mp3",
        ]

        found_files = []
        for filename in expected_files:
            filepath = os.path.join(output_dir, filename)
            if os.path.exists(filepath):
                found_files.append(filename)

        if len(found_files) >= 2:  # At least 2 key files exist
            self.logger.info("=" * 60)
            self.logger.info("SESSION ALREADY PROCESSED")
            self.logger.info(f"Output directory: {output_dir}")
            self.logger.info(f"Found files: {', '.join(found_files)}")
            self.logger.info("=" * 60)
            return True

        return False

    def find_existing_files(self, directory):
        """Find existing video, audio, and transcript files in directory"""
        if not os.path.exists(directory):
            return None, None, None

        video_path = None
        audio_path = None
        transcript_path = None

        # Look for video files
        video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
        for file in os.listdir(directory):
            file_lower = file.lower()
            for ext in video_extensions:
                if file_lower.endswith(ext):
                    video_path = os.path.join(directory, file)
                    self.logger.info(f"Found existing video file: {file}")
                    break

        # Look for audio file
        audio_file = os.path.join(directory, "session_audio.mp3")
        if os.path.exists(audio_file):
            audio_path = audio_file
            self.logger.info(f"Found existing audio file: session_audio.mp3")

        # Look for transcript file (find the most recent one)
        transcript_files = []
        for file in os.listdir(directory):
            if file.startswith("full_transcript_") and file.endswith(".txt"):
                transcript_files.append(os.path.join(directory, file))

        if transcript_files:
            # Sort by modification time and get the most recent
            transcript_path = max(transcript_files, key=os.path.getmtime)
            self.logger.info(
                f"Found existing transcript file: {os.path.basename(transcript_path)}"
            )

        return video_path, audio_path, transcript_path

    def process_meeting(
        self,
        name_filter=None,
        file_id=None,
        output_dir=None,
        keep_temp_files=False,
        existing_dir=None,
    ):
        """Process meeting recording end-to-end"""
        self.logger.info("Starting meeting processing")
        temp_dir = None

        try:
            video_path = None
            audio_path = None
            transcript_path = None

            # Handle existing directory
            if existing_dir:
                # Check for existing files in the directory
                self.logger.info(f"Checking for existing files in: {existing_dir}")
                video_path, audio_path, transcript_path = self.find_existing_files(
                    existing_dir
                )

                # Use the existing directory as output directory
                if output_dir is None:
                    output_dir = existing_dir
                    self.logger.info(
                        f"Using existing directory as output: {output_dir}"
                    )

            # Determine output directory early if we need to download
            if not video_path and output_dir is None:
                # Create a temporary output directory name that we'll update later
                output_dir = os.path.join("output", f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                self.logger.info(f"Creating temporary output directory: {output_dir}")

            # Download from Drive if no video found
            if not video_path:
                self.logger.info("Downloading meeting recording from Google Drive...")
                # Ensure output directory exists for download
                os.makedirs(output_dir, exist_ok=True)
                
                if file_id:
                    # Download by file ID
                    video_path = self.drive_handler.download_file(file_id, output_dir)
                elif name_filter:
                    # Download by name filter
                    video_path = self.drive_handler.download_recording(name_filter, output_dir)
                else:
                    raise ValueError("Either file_id or name_filter must be provided")

            # Get proper output directory name from video filename and rename if needed
            video_filename = os.path.basename(video_path)
            proper_output_dir = self.get_output_dir_from_filename(video_filename)
            
            # If we created a temporary directory name, rename it to the proper name
            if output_dir and "session_" in output_dir and output_dir != proper_output_dir:
                if os.path.exists(output_dir) and not os.path.exists(proper_output_dir):
                    self.logger.info(f"Renaming output directory: {output_dir} -> {proper_output_dir}")
                    os.rename(output_dir, proper_output_dir)
                    # Update video_path if it was in the old directory
                    if output_dir in video_path:
                        video_path = video_path.replace(output_dir, proper_output_dir)
                output_dir = proper_output_dir
            elif output_dir is None:
                output_dir = proper_output_dir
            
            self.logger.info(f"Using output directory: {output_dir}")

            # Check if already processed
            if self.check_already_processed(output_dir):
                self.logger.info("Skipping processing - session already completed")
                return {
                    "status": "skipped",
                    "reason": "already_processed",
                    "output_dir": output_dir,
                    "video_path": video_path,
                }

            # Verify/create output directory
            self.verify_output_directory(output_dir)

            # Video should already be in the output directory if downloaded
            # Just ensure the output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Check for existing transcript in output directory if not already found
            if not transcript_path and output_dir:
                _, _, transcript_path = self.find_existing_files(output_dir)

            # No need for temporary directory - we use output directory
            # All processing happens in the output directory

            # Create progress bar for processing steps
            with tqdm(total=4, desc="Processing meeting") as pbar:
                # Extract audio (skip if already exists)
                if not audio_path:
                    pbar.set_description("Extracting audio")
                    audio_path = self.audio_processor.extract_audio(
                        video_path, output_dir
                    )
                    self.logger.info(f"Extracted audio to: {audio_path}")
                else:
                    self.logger.info(
                        f"Skipping audio extraction - using existing file: {audio_path}"
                    )
                pbar.update(1)

                pbar.set_description("Generating transcript")
                # Generate transcript (skip if already exists)
                if not transcript_path:
                    transcript, transcript_path = self.transcriber.get_transcript(
                        audio_path, output_dir
                    )
                    self.logger.info("Transcript generated successfully")
                else:
                    # Read existing transcript
                    with open(transcript_path, "r", encoding="utf-8") as f:
                        transcript = f.read()
                    self.logger.info(
                        f"Skipping transcript generation - using existing file: {transcript_path}"
                    )
                pbar.update(1)

                pbar.set_description("Processing transcript")
                # Process transcript
                processed_notes, notes_path = (
                    self.transcript_processor.process_transcript(
                        transcript_path, output_dir
                    )
                )
                self.logger.info("Transcript processed successfully")
                pbar.update(1)

                pbar.set_description("Uploading to Google Docs")
                # Upload to Google Docs
                timestamp = datetime.now().strftime("%Y%m%d")
                doc_title = f"DnD Session Notes - {timestamp}"
                doc_url = self.docs_uploader.upload_notes(notes_path, title=doc_title)
                self.logger.info(f"Notes uploaded successfully to: {doc_url}")
                pbar.update(1)

                # Save processing summary
                outputs = {
                    "video_path": video_path,
                    "transcript_path": transcript_path,
                    "notes_path": notes_path,
                    "doc_url": doc_url,
                    "timestamp": timestamp,
                }

                summary_path = os.path.join(output_dir, f"summary_{timestamp}.json")
                with open(summary_path, "w") as f:
                    json.dump(outputs, f, indent=2)
                self.logger.info(f"Processing summary saved to: {summary_path}")

                return outputs

        except Exception as e:
            self.logger.error(f"Error in process_meeting: {str(e)}")
            raise

        finally:
            # Clean up any audio processor temp files
            if not keep_temp_files:
                try:
                    self.audio_processor.cleanup()  # Clean up any audio processor temp files
                except Exception as e:
                    self.logger.warning(f"Error during cleanup: {str(e)}")


def main():
    """Main function for running the complete pipeline"""
    logger = setup_logging("MainScript")

    parser = argparse.ArgumentParser(description="Process DnD session recordings")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Process command
    process_parser = subparsers.add_parser(
        "process", help="Process a session recording"
    )
    process_parser.add_argument(
        "--output",
        "-o",
        help="Output directory (defaults to directory based on meeting name and date)",
    )
    process_parser.add_argument(
        "--keep-temp", action="store_true", help="Keep temporary files"
    )
    process_parser.add_argument(
        "--name", "-n", help="Recording name filter"
    )
    process_parser.add_argument(
        "--id", "-i", help="Google Drive file ID"
    )
    process_parser.add_argument(
        "--dir",
        "-d",
        help="Path to existing output directory (skips steps based on existing files)",
    )
    
    # Interactive command
    interactive_parser = subparsers.add_parser(
        "interactive", help="Interactively select and process a recording"
    )
    interactive_parser.add_argument(
        "--output",
        "-o",
        help="Output directory (defaults to directory based on meeting name and date)",
    )
    interactive_parser.add_argument(
        "--keep-temp", action="store_true", help="Keep temporary files"
    )

    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean up old temporary files")
    clean_parser.add_argument(
        "--output", "-o", help="Output directory", default="meeting_outputs"
    )
    clean_parser.add_argument(
        "--age", type=int, default=24, help="Maximum age in hours for temp files"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List temporary directories")
    list_parser.add_argument(
        "--output", "-o", help="Output directory", default="meeting_outputs"
    )

    args = parser.parse_args()
    logger.debug(f"Arguments parsed: {args}")

    try:
        if args.command == "process":
            # Initialize processor
            processor = MeetingProcessor()

            # Process meeting
            logger.info("Starting meeting processing pipeline...")
            
            # Validate that either name or id is provided for new downloads
            if not args.dir and not args.name and not args.id:
                print("Error: Either --name, --id, or --dir must be provided")
                print("Use --name to search by recording name")
                print("Use --id to download by Google Drive file ID")
                print("Use --dir to process an existing directory")
                return
            
            results = processor.process_meeting(
                name_filter=args.name,
                file_id=args.id,
                output_dir=args.output or args.dir,
                keep_temp_files=args.keep_temp,
                existing_dir=args.dir,
            )

            # Print summary of outputs
            print("\nProcessing Summary:")
            if results.get("status") == "skipped":
                print(f"Status: SKIPPED - {results.get('reason', 'unknown')}")
                print(f"Output Directory: {results.get('output_dir', 'N/A')}")
                print(
                    f"Video File: {os.path.basename(results.get('video_path', 'N/A'))}"
                )
                print("\nThis session has already been processed.")
                print(
                    f"Check the output directory for existing files: {results.get('output_dir', 'N/A')}"
                )
            else:
                print(f"Output Directory: {args.output or 'auto-generated'}")
                print(f"Video File: {os.path.basename(results['video_path'])}")
                print(f"Transcript: {os.path.basename(results['transcript_path'])}")
                print(f"Notes: {os.path.basename(results['notes_path'])}")
                print(f"Google Doc: {results['doc_url']}")

        elif args.command == "interactive":
            # Initialize processor
            processor = MeetingProcessor()
            
            # List available recordings
            logger.info("Fetching available recordings from Google Drive...")
            recordings = processor.drive_handler.list_recordings()
            
            if not recordings:
                print("No recordings found in the Google Drive folder.")
                return
            
            # Display recordings
            print("\nAvailable Recordings:")
            print("-" * 80)
            for rec in recordings:
                print(f"{rec['index']:2d}. {rec['file_name']}")
                print(f"    Size: {rec['file_size_mb']:.1f} MB")
                print(f"    Created: {rec['created_time'][:10]}")
                print()
            
            # Get user selection
            while True:
                try:
                    selection = input(f"Select a recording to process (1-{len(recordings)}), or 'q' to quit: ")
                    if selection.lower() == 'q':
                        print("Exiting...")
                        return
                    
                    idx = int(selection) - 1
                    if 0 <= idx < len(recordings):
                        selected = recordings[idx]
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(recordings)}")
                except ValueError:
                    print("Please enter a valid number or 'q' to quit")
            
            # Download the selected recording
            print(f"\nProcessing: {selected['file_name']}")
            print(f"Downloading {selected['file_size_mb']:.1f} MB...")
            
            # Get output directory from filename
            output_dir = args.output or processor.get_output_dir_from_filename(selected['file_name'])
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Download the file directly to output directory
            video_path = processor.drive_handler.download_file(
                selected['file_id'], output_dir
            )
            
            # Process the recording
            logger.info("Starting processing pipeline...")
            results = processor.process_meeting(
                file_id=selected['file_id'],
                output_dir=output_dir,
                keep_temp_files=args.keep_temp,
                existing_dir=output_dir  # Use output_dir as existing_dir since we downloaded there
            )
            
            # Print summary
            print("\nProcessing Summary:")
            if results.get("status") == "skipped":
                print(f"Status: SKIPPED - {results.get('reason', 'unknown')}")
                print(f"Output Directory: {results.get('output_dir', 'N/A')}")
            else:
                print(f"Output Directory: {output_dir}")
                print(f"Transcript: {os.path.basename(results['transcript_path'])}")
                print(f"Notes: {os.path.basename(results['notes_path'])}")
                print(f"Google Doc: {results['doc_url']}")

        elif args.command == "clean":
            removed, remaining = cleanup_old_temp_directories(args.output, args.age)
            print(f"\nCleaned up {removed} temporary directories")
            if remaining:
                print(f"{len(remaining)} directories remain")

        elif args.command == "list":
            dir_info = list_temp_directories(args.output)
            if dir_info:
                print("\nTemporary Directories:")
                for info in dir_info:
                    print(f"\nPath: {info['path']}")
                    print(f"Created: {info['created']}")
                    print(f"Age: {info['age_hours']} hours")
                    print(f"Size: {info['size_mb']} MB")
            else:
                print("No temporary directories found")

        else:
            parser.print_help()

    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
