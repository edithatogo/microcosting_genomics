#!/usr/bin/env python3
"""
Script to run the web interface for microcosting analysis.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.web import create_app  # noqa: E402


def main():
    """Main function to run the web application."""
    print("Starting Microcosting Analysis Web Interface...")
    print("Access the application at: http://127.0.0.1:5000")
    print("Press CTRL+C to stop the server.")
    
    try:
        app = create_app()
        app.run(debug=True, host='127.0.0.1', port=5000)
    except Exception as e:
        print(f"Error starting web application: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())