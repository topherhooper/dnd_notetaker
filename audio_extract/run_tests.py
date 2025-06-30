#!/usr/bin/env python3
"""Run all tests for the audio_extract module."""

import subprocess
import sys
from pathlib import Path

# Get the parent directory
parent_dir = Path(__file__).parent.parent

# Run pytest from parent directory
cmd = [sys.executable, "-m", "pytest", "audio_extract/tests/", "-v", "--tb=short"]

print(f"Running tests from: {parent_dir}")
print(f"Command: {' '.join(cmd)}")
print("-" * 60)

# Change to parent directory and run tests
result = subprocess.run(cmd, cwd=str(parent_dir))

sys.exit(result.returncode)
