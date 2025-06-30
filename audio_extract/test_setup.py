#!/usr/bin/env python3
"""Quick test to verify storage setup is working."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=== Audio Extract Storage Setup Test ===\n")

# Test 1: Import check
print("1. Checking imports...")
try:
    from audio_extract import StorageFactory, LocalStorageAdapter, GCSStorageAdapter

    print("✓ Storage imports working")
except ImportError as e:
    print(f"✗ Storage import failed: {e}")
    sys.exit(1)

try:
    from audio_extract.drive import StorageAwareDriveMonitor

    print("✓ StorageAwareDriveMonitor import working")
except ImportError as e:
    print(f"✗ StorageAwareDriveMonitor import failed: {e}")
    sys.exit(1)

# Test 2: Local storage creation
print("\n2. Testing local storage...")
try:
    config = {"type": "local", "local": {"path": "./test_output"}}
    storage = StorageFactory.create(config)
    print(f"✓ Created local storage at: {storage.base_path}")
except Exception as e:
    print(f"✗ Local storage creation failed: {e}")
    sys.exit(1)

# Test 3: GCS storage with missing dependency
print("\n3. Testing GCS storage (without google-cloud-storage)...")
try:
    config = {
        "type": "gcs",
        "gcs": {"bucket_name": "test-bucket", "credentials_path": "/path/to/creds.json"},
    }
    storage = StorageFactory.create(config)
    print("✗ GCS storage should have failed without google-cloud-storage!")
except Exception as e:
    if "Google Cloud Storage libraries not installed" in str(e):
        print("✓ GCS storage correctly detected missing dependency")
    else:
        print(f"✗ Unexpected error: {e}")

# Test 4: Config file check
print("\n4. Checking config files...")
config_files = ["audio_extract_config.dev.yaml", "audio_extract_config.prod.yaml"]
for config_file in config_files:
    path = Path(config_file)
    if path.exists():
        print(f"✓ Found {config_file}")
        # Check if storage section exists
        content = path.read_text()
        if "storage:" in content:
            print(f"  ✓ Storage section configured")
        else:
            print(f"  ✗ Missing storage section")
    else:
        print(f"✗ Missing {config_file}")

print("\n=== Setup test complete ===")
print("\nNext steps:")
print("1. For local storage: Just run with dev config")
print("2. For GCS with gcsfuse:")
print("   - Install gcsfuse")
print("   - Mount: gcsfuse --implicit-dirs my-bucket ~/audio-mount")
print("   - Update config: storage.local.path = ~/audio-mount")
print("3. For direct GCS API:")
print("   - Install: pip install google-cloud-storage")
print("   - Update config: storage.type = gcs")
