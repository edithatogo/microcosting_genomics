#!/usr/bin/env python3
"""
Script to test the web interface improvements.
"""

import sys
from pathlib import Path
import webbrowser
import time
import subprocess

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))


def main():
    """Main function to test the web UI improvements."""
    print("Testing Web Interface Improvements")
    print("=" * 40)
    
    # Start the web server in the background
    print("Starting web server...")
    try:
        # Run the web server in the background
        process = subprocess.Popen([
            sys.executable, "-m", "unimelb_phd_phase_1.web"
        ], cwd=src_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for the server to start
        time.sleep(3)
        
        # Check if the process is still running
        if process.poll() is None:
            print("Web server started successfully")
            print("Opening web browser to http://127.0.0.1:5000")
            
            # Open the web browser
            webbrowser.open("http://127.0.0.1:5000")
            
            print("\nWeb interface is now running!")
            print("Features to test:")
            print("1. Improved navigation with icons")
            print("2. Enhanced card-based layout")
            print("3. Better form styling")
            print("4. Improved visualization interface")
            print("5. Custom CSS styling")
            print("6. Responsive design")
            print("\nPress CTRL+C to stop the server")
            
            # Wait for the process to complete (or be interrupted)
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\nStopping web server...")
                process.terminate()
                process.wait()
                print("Web server stopped")
        else:
            stdout, stderr = process.communicate()
            print(f"Error starting web server: {stderr.decode()}")
            return 1
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())