"""Main orchestrator for processing Google Meet recordings"""

import os
import logging
from pathlib import Path
from typing import Optional
from tqdm import tqdm

from .audio_extractor import AudioExtractor
from .transcriber import Transcriber
from .note_generator import NoteGenerator
from .artifacts import Artifacts
from .simplified_drive_handler import SimplifiedDriveHandler

logger = logging.getLogger(__name__)


class MeetProcessor:
    """Orchestrates the entire Meet recording processing pipeline"""
    
    def __init__(self, config, output_dir: Path):
        self.config = config
        self.output_dir = output_dir
        
        # Initialize components with config
        self.drive_handler = SimplifiedDriveHandler(config.service_account_path, config)
        self.audio_extractor = AudioExtractor(config)
        self.transcriber = Transcriber(config.openai_api_key, config)
        self.note_generator = NoteGenerator(config.openai_api_key, config)
        self.artifacts = Artifacts(output_dir, config)
        
    def process(self, file_id: Optional[str] = None):
        """Process a Google Meet recording from start to finish"""
        
        # Step 1: Download video from Google Drive
        with tqdm(total=5, desc="Processing", unit="step") as pbar:
            logger.info("📥 Downloading recording from Google Drive...")
            video_path = self._download_video(file_id)
            pbar.update(1)
            
            # Step 2: Extract audio (with checkpointing)
            audio_path = self.output_dir / "audio.mp3"
            if audio_path.exists() and not self.config.dry_run:
                logger.info("✓ Audio already extracted, skipping...")
            else:
                logger.info("🎵 Extracting audio from video...")
                self.audio_extractor.extract(video_path, audio_path)
            pbar.update(1)
            
            # Step 3: Transcribe audio (with checkpointing)
            transcript_path = self.output_dir / "transcript.txt"
            if transcript_path.exists() and not self.config.dry_run:
                logger.info("✓ Transcript exists, skipping...")
                with open(transcript_path, 'r') as f:
                    transcript_text = f.read()
            else:
                logger.info("📝 Transcribing audio...")
                transcript_text = self.transcriber.transcribe(audio_path)
                if not self.config.dry_run:
                    with open(transcript_path, 'w') as f:
                        f.write(transcript_text)
            pbar.update(1)
            
            # Step 4: Generate notes (always run for quality improvements)
            logger.info("📖 Generating narrative notes...")
            notes_path = self.output_dir / "notes.txt"
            notes_text = self.note_generator.generate(transcript_text)
            if not self.config.dry_run:
                with open(notes_path, 'w') as f:
                    f.write(notes_text)
            pbar.update(1)
            
            # Step 5: Create shareable artifacts
            logger.info("🔗 Creating shareable artifacts...")
            share_url = self.artifacts.create_share_bundle(
                video_path=video_path,
                audio_path=audio_path,
                transcript_path=transcript_path,
                notes_path=notes_path
            )
            pbar.update(1)
        
        logger.info(f"\n🎉 Share your meeting notes: {share_url}")
        
    def _download_video(self, file_id: Optional[str] = None) -> Path:
        """Download video from Google Drive with checkpointing"""
        standard_path = self.output_dir / "meeting.mp4"
        
        # Check if video already exists
        if standard_path.exists() and standard_path.stat().st_size > 0 and not self.config.dry_run:
            logger.info("✓ Video already downloaded, skipping...")
            return standard_path
        
        if file_id:
            # Download specific file
            video_path = self.drive_handler.download_file(file_id, self.output_dir)
        else:
            # Download most recent recording
            video_path = self.drive_handler.download_most_recent(self.output_dir)
        
        # Rename to standard name if needed
        if video_path != standard_path and not self.config.dry_run:
            if standard_path.exists():
                standard_path.unlink()  # Remove any partial file
            video_path.rename(standard_path)
        
        return standard_path