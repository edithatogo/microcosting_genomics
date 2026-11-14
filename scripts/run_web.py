#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to run the web interface for microcosting analysis."""

import logging
import sys

from genomics_microcosting.web import create_app

logger = logging.getLogger(__name__)


def main() -> int:
    """Run the web application."""
    sys.stdout.write("Starting Microcosting Analysis Web Interface..." + "\n")
    sys.stdout.write("Access the application at: http://127.0.0.1:5000" + "\n")
    sys.stdout.write("Press CTRL+C to stop the server." + "\n")

    try:
        app = create_app()
        app.run(debug=True, host="127.0.0.1", port=5000)
    except Exception as e:
        logger.exception("Could not complete run web")
        sys.stdout.write(f"Error starting web application: {e}" + "\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
