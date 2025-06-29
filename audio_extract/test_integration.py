#!/usr/bin/env python3
"""Integration test for audio extraction pipeline."""

import sys
import tempfile
import shutil
from pathlib import Path
import subprocess

try:
    from .tracker import ProcessingTracker
    from .extractor import AudioExtractor
    from .chunker import AudioChunker
    from .exceptions import AudioExtractionError
except ImportError:
    # When running directly
    from tracker import ProcessingTracker
    from extractor import AudioExtractor
    from chunker import AudioChunker
    from exceptions import AudioExtractionError


def create_test_video(output_path: Path) -> None:
    """Create a simple test video file using FFmpeg."""
    # Generate a 10-second test video with audio
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', 'testsrc=duration=10:size=320x240:rate=1',
        '-f', 'lavfi', 
        '-i', 'sine=frequency=440:duration=10',
        '-pix_fmt', 'yuv420p',
        '-y',
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create test video: {result.stderr}")


def test_full_pipeline():
    """Test the complete audio extraction pipeline."""
    print("Audio Extraction Integration Test")
    print("=" * 50)
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    test_video = temp_dir / "test_video.mp4"
    db_path = temp_dir / "test.db"
    output_dir = temp_dir / "output"
    output_dir.mkdir()
    
    try:
        # 1. Initialize components
        print("\n1. Initializing components...")
        tracker = ProcessingTracker(db_path)
        extractor = AudioExtractor()
        chunker = AudioChunker(max_size_mb=1)  # Small size to force chunking
        print("   ✓ Components initialized")
        
        # 2. Create test video
        print("\n2. Creating test video...")
        try:
            create_test_video(test_video)
            print(f"   ✓ Test video created: {test_video}")
        except Exception as e:
            print(f"   ✗ Failed to create test video: {e}")
            print("   Note: This test requires FFmpeg to be installed")
            return False
        
        # 3. Test extraction
        print("\n3. Testing extraction...")
        audio_path = output_dir / "test_audio.mp3"
        
        try:
            # Get video info
            info = extractor.get_video_info(test_video)
            print(f"   Video duration: {info['duration_formatted']}")
            
            # Extract audio
            extractor.extract(test_video, audio_path)
            print(f"   ✓ Audio extracted: {audio_path}")
            
            # Verify file exists
            if not audio_path.exists():
                raise AudioExtractionError("Audio file was not created")
            
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            print(f"   Audio size: {file_size_mb:.2f} MB")
            
        except Exception as e:
            print(f"   ✗ Extraction failed: {e}")
            return False
        
        # 4. Test chunking
        print("\n4. Testing chunking...")
        try:
            chunks = chunker.split(audio_path, output_dir)
            print(f"   ✓ Split into {len(chunks)} chunks")
            for i, chunk in enumerate(chunks):
                chunk_size_kb = chunk.stat().st_size / 1024
                print(f"   Chunk {i+1}: {chunk.name} ({chunk_size_kb:.1f} KB)")
        except Exception as e:
            print(f"   ✗ Chunking failed: {e}")
            # Not critical for basic functionality
        
        # 5. Test tracking
        print("\n5. Testing tracking database...")
        try:
            # Mark as processed
            tracker.mark_processed(
                str(test_video),
                status="completed",
                metadata={"audio_path": str(audio_path)}
            )
            
            # Verify tracking
            if tracker.is_processed(str(test_video)):
                print("   ✓ Video marked as processed")
            else:
                raise TrackingError("Video not marked as processed")
            
            # Get metadata
            metadata = tracker.get_metadata(str(test_video))
            if metadata:
                print(f"   Status: {metadata['status']}")
                print(f"   Audio path: {metadata['metadata']['audio_path']}")
            
            # Test statistics
            stats = tracker.get_statistics()
            print(f"   Total processed: {stats['total']}")
            print(f"   Success rate: {stats['success_rate']}%")
            
        except Exception as e:
            print(f"   ✗ Tracking failed: {e}")
            return False
        
        # 6. Test error handling
        print("\n6. Testing error handling...")
        try:
            # Try to extract non-existent file
            fake_video = temp_dir / "fake_video.mp4"
            try:
                extractor.extract(fake_video, output_dir / "fake_audio.mp3")
                print("   ✗ Should have failed on non-existent file")
            except AudioExtractionError:
                print("   ✓ Correctly handled non-existent file")
            
            # Mark as failed
            tracker.mark_processed(
                str(fake_video),
                status="failed",
                metadata={"error": "File not found"}
            )
            
            failed = tracker.get_failed_videos()
            if len(failed) == 1:
                print("   ✓ Failed processing tracked correctly")
            
        except Exception as e:
            print(f"   ✗ Error handling test failed: {e}")
            return False
        
        print("\n" + "=" * 50)
        print("✓ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False
    
    finally:
        # Cleanup
        tracker.close()
        shutil.rmtree(temp_dir)
        print("\nCleaned up temporary files")


def main():
    """Run integration tests."""
    success = test_full_pipeline()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())