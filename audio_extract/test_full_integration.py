#!/usr/bin/env python3
"""Full integration test for audio_extract module."""

import subprocess
import sys
import tempfile
import shutil
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return result."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.returncode == 0, result.stdout, result.stderr


def create_test_video(output_path):
    """Create a small test video with audio."""
    cmd = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=3:size=320x240:rate=1",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=3",
        "-pix_fmt",
        "yuv420p",
        "-y",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def main():
    print("Running full integration test...")
    print("=" * 60)

    parent_dir = Path(__file__).parent.parent

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        video_path = temp_path / "test_video.mp4"
        output_dir = temp_path / "output"
        output_dir.mkdir()
        db_path = temp_path / "test.db"

        # Test 1: Create test video
        print("\n1. Creating test video...")
        if create_test_video(video_path):
            print("✓ Test video created")
        else:
            print("✗ Failed to create test video (FFmpeg required)")
            print("  Skipping video-dependent tests")
            video_path = None

        # Test 2: Test extraction with tracking
        if video_path and video_path.exists():
            print("\n2. Testing audio extraction with tracking...")
            cmd = f"{sys.executable} -m audio_extract.dev_extract --video {video_path} --output {output_dir} --db {db_path}"
            success, stdout, stderr = run_command(cmd, cwd=str(parent_dir))

            if success:
                print("✓ Audio extraction successful")
                # Check if audio file was created
                audio_files = list(output_dir.glob("*.mp3"))
                if audio_files:
                    print(f"  Created: {audio_files[0].name}")
            else:
                print("✗ Audio extraction failed")
                print(f"  Error: {stderr}")

        # Test 3: Check processing status
        print("\n3. Testing processing status...")
        cmd = f"{sys.executable} -m audio_extract.dev_status --db {db_path} --stats"
        success, stdout, stderr = run_command(cmd, cwd=str(parent_dir))

        if success and "Total videos: 1" in stdout:
            print("✓ Processing tracked correctly")
            print("  " + stdout.strip().replace("\n", "\n  "))
        else:
            print("✗ Processing status check failed")

        # Test 4: Test with already processed video
        if video_path and video_path.exists():
            print("\n4. Testing duplicate processing detection...")
            cmd = f"{sys.executable} -m audio_extract.dev_extract --video {video_path} --output {output_dir} --db {db_path}"
            success, stdout, stderr = run_command(cmd, cwd=str(parent_dir))

            if success and "already processed" in stdout:
                print("✓ Duplicate processing detected")
            else:
                print("✗ Duplicate detection failed")

        # Test 5: Test dry-run mode
        print("\n5. Testing dry-run mode...")
        another_video = temp_path / "another_video.mp4"
        another_video.touch()  # Just create empty file for dry-run

        cmd = f"{sys.executable} -m audio_extract.dev_extract --video {another_video} --output {output_dir} --dry-run"
        success, stdout, stderr = run_command(cmd, cwd=str(parent_dir))

        if success and "[DRY RUN]" in stdout:
            print("✓ Dry-run mode works")
        else:
            print("✗ Dry-run mode failed")

        # Test 6: Test the Python API directly
        print("\n6. Testing Python API...")
        test_api_script = temp_path / "test_api.py"
        test_api_script.write_text(
            f"""
import sys
sys.path.insert(0, '{parent_dir}')

from audio_extract import ProcessingTracker

tracker = ProcessingTracker('{db_path}')
stats = tracker.get_statistics()
print(f"API Stats: total={{stats['total']}}, completed={{stats['completed']}}")
tracker.close()
"""
        )

        cmd = f"{sys.executable} {test_api_script}"
        success, stdout, stderr = run_command(cmd)

        if success and "API Stats:" in stdout:
            print("✓ Python API works")
            print("  " + stdout.strip())
        else:
            print("✗ Python API failed")
            if stderr:
                print(f"  Error: {stderr}")

    print("\n" + "=" * 60)
    print("Integration testing completed!")


if __name__ == "__main__":
    main()
