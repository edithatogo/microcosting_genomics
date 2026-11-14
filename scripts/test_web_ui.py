#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to test the web interface improvements."""

import logging
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

logger = logging.getLogger(__name__)

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))


def main() -> int:
    """Test the web UI improvements."""
    sys.stdout.write("Testing Web Interface Improvements" + "\n")
    sys.stdout.write(str("=" * 40) + "\n")

    # Start the web server in the background
    sys.stdout.write("Starting web server..." + "\n")
    try:
        # Run the web server in the background
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "genomics_microcosting.web",
            ],
            cwd=src_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait a moment for the server to start
        time.sleep(3)

        # Check if the process is still running
        if process.poll() is None:
            sys.stdout.write("Web server started successfully" + "\n")
            sys.stdout.write("Opening web browser to http://127.0.0.1:5000" + "\n")

            # Open the web browser
            webbrowser.open("http://127.0.0.1:5000")

            sys.stdout.write("\nWeb interface is now running!" + "\n")
            sys.stdout.write("Features to test:" + "\n")
            sys.stdout.write("1. Improved navigation with icons" + "\n")
            sys.stdout.write("2. Enhanced card-based layout" + "\n")
            sys.stdout.write("3. Better form styling" + "\n")
            sys.stdout.write("4. Improved visualization interface" + "\n")
            sys.stdout.write("5. Custom CSS styling" + "\n")
            sys.stdout.write("6. Responsive design" + "\n")
            sys.stdout.write("\nPress CTRL+C to stop the server" + "\n")

            # Wait for the process to complete (or be interrupted)
            try:
                process.wait()
            except KeyboardInterrupt:
                sys.stdout.write("\nStopping web server..." + "\n")
                process.terminate()
                process.wait()
                sys.stdout.write("Web server stopped" + "\n")
        else:
            _stdout, stderr = process.communicate()
            sys.stdout.write(f"Error starting web server: {stderr.decode()}" + "\n")
            return 1

    except Exception as e:
        logger.exception("Could not complete test web ui")
        sys.stdout.write(f"Error: {e}" + "\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
