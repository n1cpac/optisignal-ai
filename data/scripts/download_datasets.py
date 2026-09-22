#!/usr/bin/env python3
"""
Dataset download script for OptiSignal-AI

Downloads traffic light datasets from public sources.
Supports: LISA, BSTLD, DTLD

Usage:
    python download_datasets.py --dataset lisa --output ../datasets/
    python download_datasets.py --dataset bstld --output ../datasets/
    python download_datasets.py --dataset dtld --output ../datasets/
"""

import argparse
import os
from pathlib import Path


def download_lisa(output_dir: str) -> bool:
    """
    Download LISA Traffic Light Dataset from Kaggle.
    
    Args:
        output_dir: Directory to save the dataset
        
    Returns:
        True if successful, False otherwise
    """
    print("\n" + "="*70)
    print("LISA Traffic Light Dataset")
    print("="*70)
    print("\nDataset: LISA Traffic Light Dataset")
    print("Source: https://www.kaggle.com/datasets/mbornstein/lisa-traffic-light-dataset")
    print("Size: ~2.5 GB")
    print("\nInstructions:")
    print("1. Go to: https://www.kaggle.com/datasets/mbornstein/lisa-traffic-light-dataset")
    print("2. Click 'Download' button")
    print("3. Extract the ZIP file to:", os.path.join(output_dir, "LISA"))
    print("\n" + "="*70)
    return True


def download_bstld(output_dir: str) -> bool:
    """
    Download Bosch Small Traffic Lights Dataset.
    
    Args:
        output_dir: Directory to save the dataset
        
    Returns:
        True if successful, False otherwise
    """
    print("\n" + "="*70)
    print("Bosch Small Traffic Lights Dataset (BSTLD)")
    print("="*70)
    print("\nDataset: BSTLD")
    print("Source: https://hci.iwr.uni-heidelberg.de/node/6132")
    print("Size: ~1.2 GB")
    print("\nInstructions:")
    print("1. Go to: https://hci.iwr.uni-heidelberg.de/node/6132")
    print("2. Register (free account required)")
    print("3. Download the dataset")
    print("4. Extract to:", os.path.join(output_dir, "BSTLD"))
    print("\n" + "="*70)
    return True


def download_dtld(output_dir: str) -> bool:
    """
    Download DriveU Traffic Light Dataset.
    
    Args:
        output_dir: Directory to save the dataset
        
    Returns:
        True if successful, False otherwise
    """
    print("\n" + "="*70)
    print("DriveU Traffic Light Dataset (DTLD)")
    print("="*70)
    print("\nDataset: DTLD")
    print("Source: https://www.uni-tuebingen.de/en/faculties/faculty-of-science/departments/computer-science/chair-of-autonomous-vision/datasets/")
    print("Size: ~5.0 GB")
    print("\nInstructions:")
    print("1. Go to: https://www.uni-tuebingen.de/...")
    print("2. Register (free account required)")
    print("3. Download the dataset")
    print("4. Extract to:", os.path.join(output_dir, "DTLD"))
    print("\n" + "="*70)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Download traffic light datasets for OptiSignal-AI"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        choices=["lisa", "bstld", "dtld", "all"],
        default="all",
        help="Dataset to download (default: all)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="../datasets/",
        help="Output directory for datasets (default: ../datasets/)"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "#"*70)
    print("# OptiSignal-AI Dataset Download Tool")
    print("#"*70)
    print(f"\nOutput directory: {output_dir.absolute()}")
    
    # Download selected datasets
    if args.dataset in ["lisa", "all"]:
        download_lisa(str(output_dir))
    
    if args.dataset in ["bstld", "all"]:
        download_bstld(str(output_dir))
    
    if args.dataset in ["dtld", "all"]:
        download_dtld(str(output_dir))
    
    print("\n" + "#"*70)
    print("# Download Instructions Complete")
    print("#"*70)
    print("\nNext steps:")
    print("1. Download datasets manually from the URLs above")
    print("2. Extract to the specified directories")
    print("3. Run: python convert_to_yolo.py")
    print("4. Run: python partition_dataset.py")
    print("5. Run: python validate_dataset.py")
    print("\n")


if __name__ == "__main__":
    main()
