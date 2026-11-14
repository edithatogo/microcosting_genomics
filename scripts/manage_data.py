#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to manage data versions and metadata."""

import argparse
import logging
import sys
import traceback
from pathlib import Path

from genomics_microcosting.data_management import DataManager

logger = logging.getLogger(__name__)


def _register(dm: DataManager, filename: str | None) -> int:
    if not filename:
        sys.stdout.write("Error: --file is required for register action\n")
        return 1
    file_path = Path(filename)
    if not file_path.exists():
        sys.stdout.write(f"Error: File not found: {file_path}\n")
        return 1
    version_id = dm.register_dataset(file_path)
    sys.stdout.write(f"Registered {file_path} with version {version_id}\n")
    return 0


def _load(
    dm: DataManager,
    dataset: str,
    version: str | None,
    output: str | None,
) -> None:
    df = dm.load_dataset(dataset, version)
    sys.stdout.write(f"Loaded dataset {dataset} with shape {df.shape}\n")
    if output:
        output_path = Path(output)
        if output_path.suffix.lower() == ".csv":
            df.to_csv(output_path, index=False)
        else:
            df.to_parquet(output_path, index=False)
        sys.stdout.write(f"Saved to {output_path}\n")
    else:
        sys.stdout.write(f"{df.head()}\n")


def _perform_action(dm: DataManager, args: argparse.Namespace) -> int:
    if args.action == "register":
        return _register(dm, args.file)
    if args.action == "list":
        sys.stdout.write("Registered datasets:\n")
        sys.stdout.writelines(f"  {dataset}\n" for dataset in dm.list_datasets())
        return 0
    if not args.dataset:
        sys.stdout.write(f"Error: --dataset is required for {args.action} action\n")
        return 1
    if args.action == "info":
        info = dm.get_dataset_info(args.dataset)
        sys.stdout.write(f"Dataset info for {args.dataset}:\n")
        sys.stdout.writelines(f"  {key}: {value}\n" for key, value in info.items())
    elif args.action == "load":
        _load(dm, args.dataset, args.version, args.output)
    elif dm.verify_integrity(args.dataset, args.version):
        sys.stdout.write(f"Dataset {args.dataset} integrity verified\n")
    else:
        sys.stdout.write(f"Dataset {args.dataset} integrity check failed\n")
        return 1
    return 0


def main() -> int:
    """Manage data."""
    parser = argparse.ArgumentParser(description="Manage data versions and metadata")
    parser.add_argument("--data-dir", help="Path to data directory")
    parser.add_argument("--metadata-dir", help="Path to metadata directory")
    parser.add_argument(
        "--action",
        choices=["register", "list", "info", "load", "verify"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument("--file", help="File to register")
    parser.add_argument("--dataset", help="Dataset name for info/load/verify actions")
    parser.add_argument("--version", help="Specific version to load/verify")
    parser.add_argument("--output", help="Output file for loaded data")

    args = parser.parse_args()

    try:
        # Set up data manager
        if args.data_dir:
            data_dir = Path(args.data_dir)
        else:
            data_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"

        if args.metadata_dir:
            metadata_dir = Path(args.metadata_dir)
        else:
            metadata_dir = Path(__file__).resolve().parents[1] / "data" / "metadata"

        dm = DataManager(data_dir, metadata_dir)

        return _perform_action(dm, args)

    except Exception as e:
        logger.exception("Could not complete manage data")
        sys.stdout.write(f"Error: {e}" + "\n")

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
