#!/usr/bin/env python3
"""Development tool for Google Drive monitoring.

Run from parent directory:
    python -m audio_extract.dev_monitor --help
"""

from .cli.monitor import main

if __name__ == "__main__":
    main()
