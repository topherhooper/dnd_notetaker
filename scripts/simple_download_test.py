#!/usr/bin/env python3
"""Simple test to download the file without the full pipeline"""

import os
import sys
import json

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.dnd_notetaker.email_handler import EmailHandler

# Load config
with open('.credentials/config.json') as f:
    config = json.load(f)

print("Starting simple download test...")
handler = EmailHandler(config['email'])

# Create a test directory
os.makedirs("simple_test_download", exist_ok=True)

try:
    print("\nAttempting to download...")
    result = handler.download_meet_recording(
        subject_filter="Meeting records",
        download_dir="simple_test_download"
    )
    
    print(f"\n✓ Download successful!")
    print(f"File: {result}")
    
    # Check file size
    size = os.path.getsize(result)
    print(f"Size: {size / (1024*1024*1024):.2f} GB")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\nDone.")