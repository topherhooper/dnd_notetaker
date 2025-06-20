#!/usr/bin/env python3
"""
meet_notes - Simplified Google Meet recording processor

Usage:
    python -m meet_notes              # Process most recent recording
    python -m meet_notes FILE_ID      # Process specific recording
    python -m meet_notes --dry-run    # Show what would happen without executing
"""

import sys
import os
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

from .meet_processor import MeetProcessor
from .config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for meet_notes"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Process Google Meet recordings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
python -m dnd_notetaker                    # Process most recent recording
python -m dnd_notetaker FILE_ID            # Process specific recording
python -m dnd_notetaker FILE_ID --dry-run  # Show what would happen
python -m dnd_notetaker --dry-run          # Dry run with most recent
"""
    )
    parser.add_argument('file_id', nargs='?', help='Google Drive file ID to process')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would happen without executing operations')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--output-dir', type=str, help='Output directory path')
    
    args = parser.parse_args()
    
    # Load configuration with dry_run flag
    config = Config(config_path=args.config, dry_run=args.dry_run)
    
    # Override output directory if specified
    if args.output_dir:
        config.output_dir = Path(args.output_dir)
    
    # Find or create output directory
    # If we have existing directories with the video file, reuse them
    output_dir = None
    if config.output_dir.exists():
        for existing_dir in sorted(config.output_dir.iterdir(), reverse=True):
            if existing_dir.is_dir() and (existing_dir / "meeting.mp4").exists():
                logger.info(f"📁 Found existing output directory: {existing_dir}")
                output_dir = existing_dir
                break
    
    # Create new directory if none found
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        output_dir = config.output_dir / timestamp
        if not config.dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Created new output directory: {output_dir}")
        else:
            logger.info(f"[DRY RUN] Would create output directory: {output_dir}")
    
    # Process the recording
    processor = MeetProcessor(config, output_dir)
    
    if config.dry_run:
        logger.info("🎬 Starting Google Meet recording processor (DRY RUN)...")
    else:
        logger.info("🎬 Starting Google Meet recording processor...")
    
    processor.process(args.file_id)
    
    logger.info(f"\n✅ Processing complete!")
    logger.info(f"📁 Output saved to: {output_dir}")


if __name__ == "__main__":
    main()