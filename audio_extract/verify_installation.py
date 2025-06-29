#!/usr/bin/env python3
"""Verify the audio_extract module installation and usage."""

import subprocess
import sys
from pathlib import Path

def check_command(description, command, cwd=None):
    """Check if a command works."""
    print(f"\n{description}")
    print(f"Command: {command}")
    
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        cwd=cwd
    )
    
    if result.returncode == 0:
        print("✅ Works!")
        return True
    else:
        print("❌ Failed")
        if result.stderr:
            print(f"   Error: {result.stderr.strip()[:100]}...")
        return False

def main():
    print("Audio Extract Module - Installation Verification")
    print("=" * 60)
    
    parent_dir = Path(__file__).parent.parent
    module_dir = Path(__file__).parent
    
    print("\n1. WORKING COMMANDS:")
    print("-" * 40)
    
    # Commands that work
    working_commands = [
        ("Extract audio (dry-run)", 
         "python -m audio_extract.dev_extract --video test.mp4 --output ./output --dry-run",
         parent_dir),
        
        ("Check status", 
         "python -m audio_extract.dev_status --help",
         parent_dir),
        
        ("Run dashboard", 
         "python -m audio_extract.dev_server --help",
         parent_dir),
        
        ("Run tests",
         "python run_tests.py",
         module_dir),
        
        ("Run all tests",
         "python run_all_tests.py",
         module_dir),
    ]
    
    for desc, cmd, cwd in working_commands:
        check_command(desc, cmd, str(cwd))
    
    print("\n\n2. PYTHON API USAGE:")
    print("-" * 40)
    print("""
# From parent directory (/workspaces/dnd_notetaker):
from audio_extract import AudioExtractor, ProcessingTracker

# Extract audio
extractor = AudioExtractor()
extractor.extract('video.mp4', 'audio.mp3')

# Track processing
tracker = ProcessingTracker('processed.db')
tracker.mark_processed('video.mp4', status='completed')
""")
    
    print("\n3. RECOMMENDED USAGE:")
    print("-" * 40)
    print("""
1. Navigate to parent directory:
   cd /workspaces/dnd_notetaker

2. Use the module:
   python -m audio_extract.dev_extract --video input.mp4 --output ./output
   python -m audio_extract.dev_status --stats
   python -m audio_extract.dev_server --port 8080

3. Or use in Python scripts:
   from audio_extract import AudioExtractor
   extractor = AudioExtractor()
   extractor.extract('video.mp4', 'audio.mp3')
""")
    
    print("\n" + "=" * 60)
    print("Verification complete!")

if __name__ == "__main__":
    main()