#!/usr/bin/env python3
"""Run all tests for the audio_extract module."""

import subprocess
import sys
from pathlib import Path


def run_test(name, command):
    """Run a test and report results."""
    print(f"\n{'=' * 60}")
    print(f"Running: {name}")
    print("=" * 60)

    result = subprocess.run(command, shell=True, capture_output=False)  # Show output directly

    if result.returncode == 0:
        print(f"\n✅ {name} PASSED")
    else:
        print(f"\n❌ {name} FAILED")

    return result.returncode == 0


def main():
    print("Audio Extract Module - Comprehensive Test Suite")
    print("=" * 60)

    results = []

    # 1. Unit Tests
    results.append(run_test("Unit Tests (51 tests)", "python run_tests.py"))

    # 2. CLI Tools Test
    results.append(run_test("CLI Tools Test", "python test_cli_tools.py"))

    # 3. Dashboard Test
    results.append(run_test("Dashboard Server Test", "python test_dashboard.py"))

    # 4. Full Integration Test
    results.append(run_test("Full Integration Test", "python test_full_integration.py"))

    # Summary
    print(f"\n{'=' * 60}")
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed! The audio_extract module is ready for use.")
        print("\nTo use the module:")
        print("1. Create a virtual environment: python -m venv venv")
        print("2. Activate it: source venv/bin/activate")
        print("3. Install the module: pip install -e .")
        print("4. Use the CLI tools:")
        print("   - audio-extract --video input.mp4 --output ./output")
        print("   - audio-status --recent 7")
        print("   - audio-dashboard --port 8080")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the output above.")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
