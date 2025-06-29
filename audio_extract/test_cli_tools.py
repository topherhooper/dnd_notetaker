#!/usr/bin/env python3
"""Test CLI tools functionality."""

import subprocess
import sys
from pathlib import Path
import tempfile
import shutil

def run_command(cmd, cwd=None):
    """Run a command and return success status and output."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=cwd
    )
    return result.returncode == 0, result.stdout, result.stderr

def main():
    print("Testing CLI tools functionality...")
    print("=" * 60)
    
    # Get the module directory
    module_dir = Path(__file__).parent
    parent_dir = module_dir.parent
    
    # Test 1: Run dev_extract.py with --help
    print("\n1. Testing dev_extract.py --help")
    cmd = f"{sys.executable} -m audio_extract.dev_extract --help"
    success, stdout, stderr = run_command(cmd, cwd=str(parent_dir))
    if success and "Test audio extraction from video files" in stdout:
        print("✓ dev_extract.py help works")
    else:
        print("✗ dev_extract.py help failed")
        print(f"Error: {stderr}")
    
    # Test 2: Run dev_status.py with --help
    print("\n2. Testing dev_status.py --help")
    cmd = f"{sys.executable} -m audio_extract.dev_status --help"
    success, stdout, stderr = run_command(cmd, cwd=str(parent_dir))
    if success and "Check audio extraction processing status" in stdout:
        print("✓ dev_status.py help works")
    else:
        print("✗ dev_status.py help failed")
        print(f"Error: {stderr}")
    
    # Test 3: Run dev_server.py with --help
    print("\n3. Testing dev_server.py --help")
    cmd = f"{sys.executable} -m audio_extract.dev_server --help"
    success, stdout, stderr = run_command(cmd, cwd=str(parent_dir))
    if success and "Run the audio extraction status dashboard" in stdout:
        print("✓ dev_server.py help works")
    else:
        print("✗ dev_server.py help failed")
        print(f"Error: {stderr}")
    
    # Test 4: Test dry-run extraction
    print("\n4. Testing dry-run extraction")
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a dummy video file
        video_path = Path(temp_dir) / "test.mp4"
        video_path.touch()
        
        cmd = f"{sys.executable} -m audio_extract.dev_extract --video {video_path} --output {temp_dir} --dry-run"
        success, stdout, stderr = run_command(cmd, cwd=str(parent_dir))
        if success and "[DRY RUN]" in stdout:
            print("✓ Dry-run extraction works")
        else:
            print("✗ Dry-run extraction failed")
            print(f"Output: {stdout}")
            print(f"Error: {stderr}")
    
    # Test 5: Test status checking with non-existent DB
    print("\n5. Testing status check with new database")
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        cmd = f"{sys.executable} -m audio_extract.dev_status --db {db_path} --stats"
        success, stdout, stderr = run_command(cmd, cwd=str(parent_dir))
        if not success and "Database not found" in stderr:
            print("✓ Status check handles missing database correctly")
        else:
            print("✗ Status check failed")
            print(f"Error: {stderr}")
    
    print("\n" + "=" * 60)
    print("CLI tools testing completed!")

if __name__ == "__main__":
    main()