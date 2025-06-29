#!/usr/bin/env python3
"""Test dashboard server functionality."""

import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
import threading

def start_server(port=8888):
    """Start the dashboard server in a subprocess."""
    parent_dir = Path(__file__).parent.parent
    cmd = [
        sys.executable,
        '-m', 'audio_extract.dev_server',
        '--port', str(port),
        '--db', 'test_dashboard.db'
    ]
    
    # Start server
    proc = subprocess.Popen(
        cmd,
        cwd=str(parent_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give it time to start
    time.sleep(2)
    
    return proc

def test_endpoint(url):
    """Test if an endpoint is accessible."""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status == 200, response.read().decode()
    except urllib.error.URLError as e:
        return False, str(e)

def main():
    print("Testing dashboard server functionality...")
    print("=" * 60)
    
    # Start the server
    print("\n1. Starting dashboard server on port 8888...")
    server_proc = start_server(8888)
    
    if server_proc.poll() is not None:
        print("✗ Server failed to start")
        stdout, stderr = server_proc.communicate()
        print(f"Error: {stderr}")
        return
    
    print("✓ Server started")
    
    # Test endpoints
    base_url = "http://localhost:8888"
    
    # Test 2: Root endpoint
    print("\n2. Testing root endpoint (/)...")
    success, content = test_endpoint(base_url + "/")
    if success and "Audio Extraction Status Dashboard" in content:
        print("✓ Dashboard HTML served correctly")
    else:
        print("✗ Failed to load dashboard")
    
    # Test 3: Static CSS
    print("\n3. Testing static CSS...")
    success, content = test_endpoint(base_url + "/static/style.css")
    if success and "--primary-color" in content:
        print("✓ Static CSS served correctly")
    else:
        print("✗ Failed to load CSS")
    
    # Test 4: Static JS
    print("\n4. Testing static JavaScript...")
    success, content = test_endpoint(base_url + "/static/app.js")
    if success and "loadDashboard" in content:
        print("✓ Static JavaScript served correctly")
    else:
        print("✗ Failed to load JavaScript")
    
    # Test 5: API stats endpoint
    print("\n5. Testing API stats endpoint...")
    success, content = test_endpoint(base_url + "/api/stats")
    if success:
        print("✓ API stats endpoint working")
        # Should return JSON with statistics
        import json
        try:
            stats = json.loads(content)
            print(f"  Stats: {stats}")
        except:
            pass
    else:
        print("✗ API stats endpoint failed")
    
    # Test 6: API recent endpoint
    print("\n6. Testing API recent endpoint...")
    success, content = test_endpoint(base_url + "/api/recent?days=7")
    if success:
        print("✓ API recent endpoint working")
    else:
        print("✗ API recent endpoint failed")
    
    # Clean up
    print("\n7. Shutting down server...")
    server_proc.terminate()
    server_proc.wait(timeout=5)
    print("✓ Server shut down cleanly")
    
    # Clean up test database
    db_path = Path(__file__).parent.parent / "test_dashboard.db"
    if db_path.exists():
        db_path.unlink()
    
    print("\n" + "=" * 60)
    print("Dashboard testing completed!")

if __name__ == "__main__":
    main()