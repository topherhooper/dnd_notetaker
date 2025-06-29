#!/usr/bin/env python3
"""Development tool for checking processing status."""

import argparse
import sys
from pathlib import Path
from datetime import datetime

from .tracker import ProcessingTracker
from .exceptions import TrackingError


def format_timestamp(timestamp):
    """Format timestamp for display."""
    if isinstance(timestamp, str):
        # Parse ISO format timestamp
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    else:
        dt = timestamp
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def main():
    """Main entry point for status checking tool."""
    parser = argparse.ArgumentParser(
        description="Check audio extraction processing status"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("processed_videos.db"),
        help="Processing tracker database (default: processed_videos.db)"
    )
    parser.add_argument(
        "--recent",
        type=int,
        metavar="DAYS",
        help="Show videos processed in the last N days"
    )
    parser.add_argument(
        "--failed",
        action="store_true",
        help="Show only failed processing attempts"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show processing statistics"
    )
    parser.add_argument(
        "--check",
        type=Path,
        help="Check if a specific video file has been processed"
    )
    parser.add_argument(
        "--cleanup",
        type=int,
        metavar="DAYS",
        help="Remove entries older than N days"
    )
    parser.add_argument(
        "--reprocess",
        type=Path,
        help="Mark a video for reprocessing"
    )
    
    args = parser.parse_args()
    
    if not args.db.exists():
        print(f"✗ Database not found: {args.db}", file=sys.stderr)
        return 1
    
    try:
        tracker = ProcessingTracker(args.db)
        
        # Handle specific actions
        if args.check:
            # Check specific video
            if tracker.is_processed(str(args.check)):
                print(f"✓ Processed: {args.check}")
                metadata = tracker.get_metadata(str(args.check))
                if metadata:
                    print(f"  Status: {metadata['status']}")
                    print(f"  Processed: {format_timestamp(metadata['processed_at'])}")
                    if metadata['metadata']:
                        for key, value in metadata['metadata'].items():
                            print(f"  {key}: {value}")
            else:
                print(f"✗ Not processed: {args.check}")
            return 0
        
        if args.reprocess:
            # Mark for reprocessing
            tracker.mark_for_reprocessing(str(args.reprocess))
            print(f"✓ Marked for reprocessing: {args.reprocess}")
            return 0
        
        if args.cleanup is not None:
            # Cleanup old entries
            deleted = tracker.cleanup_old_entries(days=args.cleanup)
            print(f"✓ Removed {deleted} entries older than {args.cleanup} days")
            return 0
        
        if args.stats:
            # Show statistics
            stats = tracker.get_statistics()
            print("Processing Statistics:")
            print(f"  Total videos: {stats['total']}")
            print(f"  Completed: {stats['completed']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Success rate: {stats['success_rate']}%")
            return 0
        
        # Default action: show recent or failed videos
        if args.failed:
            videos = tracker.get_failed_videos()
            print(f"Failed Processing Attempts ({len(videos)} total):")
        else:
            days = args.recent if args.recent else 7
            videos = tracker.get_recent_processed(days=days)
            print(f"Recently Processed Videos (last {days} days, {len(videos)} total):")
        
        if not videos:
            print("  (none)")
        else:
            print("\n{:<50} {:<10} {:<20}".format("File Path", "Status", "Processed"))
            print("-" * 80)
            
            for video in videos:
                file_path = video['file_path']
                if len(file_path) > 47:
                    file_path = "..." + file_path[-44:]
                
                print("{:<50} {:<10} {:<20}".format(
                    file_path,
                    video['status'],
                    format_timestamp(video['processed_at'])
                ))
                
                # Show error details for failed videos
                if video['status'] == 'failed' and video['metadata'].get('error'):
                    error = video['metadata']['error']
                    if len(error) > 70:
                        error = error[:67] + "..."
                    print(f"    Error: {error}")
        
        return 0
        
    except TrackingError as e:
        print(f"✗ Database error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        return 1
    finally:
        if 'tracker' in locals():
            tracker.close()


if __name__ == "__main__":
    sys.exit(main())