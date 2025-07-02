#!/usr/bin/env python3
"""Development tool for testing audio extraction."""

import argparse
import sys
from pathlib import Path
import logging

from .extractor import AudioExtractor
from .chunker import AudioChunker
from .tracker import ProcessingTracker
from .exceptions import AudioExtractionError


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    """Main entry point for development extraction tool."""
    parser = argparse.ArgumentParser(description="Test audio extraction from video files")
    parser.add_argument("--video", type=Path, required=True, help="Path to input video file")
    parser.add_argument(
        "--output", type=Path, default=Path("./output"), help="Output directory (default: ./output)"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("processed_videos.db"),
        help="Processing tracker database (default: processed_videos.db)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without actually doing it"
    )
    parser.add_argument("--chunk", action="store_true", help="Split audio into chunks if needed")
    parser.add_argument(
        "--max-chunk-size", type=int, default=24, help="Maximum chunk size in MB (default: 24)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force reprocessing even if already processed"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Create mock config for dry-run mode
    class Config:
        def __init__(self, dry_run):
            self.dry_run = dry_run

    config = Config(args.dry_run)

    try:
        # Initialize components
        tracker = ProcessingTracker(args.db)
        extractor = AudioExtractor(config=config)

        # Check if already processed
        if not args.force and tracker.is_processed(str(args.video)):
            print(f"✓ Video already processed: {args.video}")
            metadata = tracker.get_metadata(str(args.video))
            if metadata:
                print(f"  Status: {metadata['status']}")
                print(f"  Processed: {metadata['processed_at']}")
                if metadata["metadata"]:
                    for key, value in metadata["metadata"].items():
                        print(f"  {key}: {value}")
            return 0

        # Ensure output directory exists
        args.output.mkdir(parents=True, exist_ok=True)

        # Get video info
        print(f"Analyzing video: {args.video}")
        info = extractor.get_video_info(args.video)
        print(f"  Duration: {info['duration_formatted']}")

        # Extract audio
        audio_path = args.output / f"{args.video.stem}_audio.mp3"
        print(f"\nExtracting audio to: {audio_path}")

        def progress_callback(percent):
            print(f"  Progress: {percent}%", end="\r")

        extractor.extract(args.video, audio_path, progress_callback=progress_callback)
        print()  # New line after progress

        # Process chunks if requested
        if args.chunk and not args.dry_run:
            chunker = AudioChunker(max_size_mb=args.max_chunk_size)
            print(f"\nChecking if chunking is needed...")
            chunks = chunker.split(audio_path, args.output)

            if len(chunks) > 1:
                print(f"✓ Split into {len(chunks)} chunks:")
                for i, chunk in enumerate(chunks):
                    print(f"  {i+1}. {chunk.name}")
            else:
                print("✓ No chunking needed")

        # Mark as processed
        if not args.dry_run:
            tracker.mark_processed(
                str(args.video),
                status="completed",
                metadata={
                    "audio_path": str(audio_path),
                    "duration": info.get("duration"),
                    "chunked": args.chunk,
                },
            )
            print(f"\n✓ Successfully processed: {args.video}")

        return 0

    except AudioExtractionError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)

        # Mark as failed
        if not args.dry_run:
            tracker.mark_processed(str(args.video), status="failed", metadata={"error": str(e)})

        return 1
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        return 1
    finally:
        if "tracker" in locals():
            tracker.close()


if __name__ == "__main__":
    sys.exit(main())
