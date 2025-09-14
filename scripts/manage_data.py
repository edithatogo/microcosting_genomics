#!/usr/bin/env python3
"""
Script to manage data versions and metadata.
"""

import sys
from pathlib import Path
import argparse

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.data_management import DataManager  # noqa: E402


def main():
    """Main function to manage data."""
    parser = argparse.ArgumentParser(description="Manage data versions and metadata")
    parser.add_argument("--data-dir", help="Path to data directory")
    parser.add_argument("--metadata-dir", help="Path to metadata directory")
    parser.add_argument("--action", choices=["register", "list", "info", "load", "verify"], 
                       required=True, help="Action to perform")
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
        
        # Perform requested action
        if args.action == "register":
            if not args.file:
                print("Error: --file is required for register action")
                return 1
            
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"Error: File not found: {file_path}")
                return 1
            
            version_id = dm.register_dataset(file_path)
            print(f"Registered {file_path} with version {version_id}")
            
        elif args.action == "list":
            datasets = dm.list_datasets()
            print("Registered datasets:")
            for dataset in datasets:
                print(f"  {dataset}")
                
        elif args.action == "info":
            if not args.dataset:
                print("Error: --dataset is required for info action")
                return 1
                
            info = dm.get_dataset_info(args.dataset)
            print(f"Dataset info for {args.dataset}:")
            for key, value in info.items():
                print(f"  {key}: {value}")
                
        elif args.action == "load":
            if not args.dataset:
                print("Error: --dataset is required for load action")
                return 1
            
            df = dm.load_dataset(args.dataset, args.version)
            print(f"Loaded dataset {args.dataset} with shape {df.shape}")
            
            if args.output:
                output_path = Path(args.output)
                if output_path.suffix.lower() == '.csv':
                    df.to_csv(output_path, index=False)
                else:
                    df.to_parquet(output_path, index=False)
                print(f"Saved to {output_path}")
            else:
                print(df.head())
                
        elif args.action == "verify":
            if not args.dataset:
                print("Error: --dataset is required for verify action")
                return 1
            
            is_valid = dm.verify_integrity(args.dataset, args.version)
            if is_valid:
                print(f"Dataset {args.dataset} integrity verified")
            else:
                print(f"Dataset {args.dataset} integrity check failed")
                return 1
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())