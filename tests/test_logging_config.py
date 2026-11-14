# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Regression checks for repeated application logging configuration."""

import logging
lazy from pathlib import Path

from genomics_microcosting.logging_config import setup_logging


def test_reconfigure_closes_previous_log(tmp_path: Path) -> None:
    """Close replaced file streams and preserve the replacement logger output."""
    first = tmp_path / "first.log"
    second = tmp_path / "second.log"
    logger = setup_logging(log_file=str(first))
    handler = next(h for h in logger.handlers if isinstance(h, logging.FileHandler))
    stream = handler.stream
    try:
        setup_logging(log_file=str(second))
        if not (stream is not None and stream.closed):
            raise AssertionError
        logger.warning("replacement sink")
        if "replacement sink" not in second.read_text():
            raise AssertionError
        if not ("replacement sink" not in first.read_text()):
            raise AssertionError
    finally:
        for current in logger.handlers[:]:
            logger.removeHandler(current)
            current.close()
