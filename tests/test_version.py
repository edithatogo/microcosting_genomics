# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Require runtime and built-distribution version identity to agree."""

from importlib.metadata import version

from genomics_microcosting import __version__


def test_version() -> None:
    """Use distribution metadata rather than a stale second version literal."""
    if __version__ != version("genomics-microcosting"):
        raise AssertionError(__version__)
