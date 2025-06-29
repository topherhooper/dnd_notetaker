#!/usr/bin/env python3
"""Development server for audio extraction status dashboard."""

import argparse
import sys
from pathlib import Path

from .dashboard.server import run_server


def main():
    """Main entry point for development server."""
    parser = argparse.ArgumentParser(
        description="Run the audio extraction status dashboard"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to run server on (default: 8080)"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("processed_videos.db"),
        help="Processing tracker database (default: processed_videos.db)"
    )
    
    args = parser.parse_args()
    
    if not args.db.exists():
        print(f"Warning: Database not found at {args.db}")
        print("The dashboard will create it when the first video is processed.")
    
    try:
        run_server(port=args.port, db_path=str(args.db))
    except KeyboardInterrupt:
        print("\nServer stopped")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())