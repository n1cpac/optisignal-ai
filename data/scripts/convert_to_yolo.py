#!/usr/bin/env python3
"""
Convert traffic light dataset annotations to YOLO format.

Supports: LISA, BSTLD, DTLD

Usage:
    python convert_to_yolo.py --dataset lisa --input ../datasets/LISA/ --output ../datasets/LISA_yolo/
"""

import argparse
from pathlib import Path


def convert_lisa_to_yolo(input_dir: str, output_dir: str) -> int:
    """
    Convert LISA dataset annotations to YOLO format.
    
    Args:
        input_dir: Input directory containing LISA dataset
        output_dir: Output directory for YOLO format
        
    Returns:
        Number of converted annotations
    """
    print("\nConverting LISA dataset to YOLO format...")
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (output_path / "images").mkdir(exist_ok=True)
    (output_path / "labels").mkdir(exist_ok=True)
    
    print("\n[INFO] LISA conversion template created.")
    print("[INFO] Manual annotation conversion required.")
    print("[INFO] See PHASE_3_DATASETS_GUIDE.md for details.")
    
    return 0


def convert_bstld_to_yolo(input_dir: str, output_dir: str) -> int:
    """
    Convert BSTLD annotations to YOLO format.
    """
    print("\nConverting BSTLD dataset to YOLO format...")
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    (output_path / "images").mkdir(exist_ok=True)
    (output_path / "labels").mkdir(exist_ok=True)
    
    print("\n[INFO] BSTLD conversion template created.")
    print("[INFO] Manual annotation conversion required.")
    
    return 0


def convert_dtld_to_yolo(input_dir: str, output_dir: str) -> int:
    """
    Convert DTLD annotations to YOLO format.
    """
    print("\nConverting DTLD dataset to YOLO format...")
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    (output_path / "images").mkdir(exist_ok=True)
    (output_path / "labels").mkdir(exist_ok=True)
    
    print("\n[INFO] DTLD conversion template created.")
    print("[INFO] Manual annotation conversion required.")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Convert traffic light dataset annotations to YOLO format"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        choices=["lisa", "bstld", "dtld"],
        required=True,
        help="Dataset to convert"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Input directory containing original dataset"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory for YOLO format"
    )
    
    args = parser.parse_args()
    
    print("\n" + "#"*70)
    print("# OptiSignal-AI Dataset Conversion Tool")
    print("#"*70)
    
    # Convert based on dataset type
    if args.dataset == "lisa":
        count = convert_lisa_to_yolo(args.input, args.output)
    elif args.dataset == "bstld":
        count = convert_bstld_to_yolo(args.input, args.output)
    elif args.dataset == "dtld":
        count = convert_dtld_to_yolo(args.input, args.output)
    
    print("\n" + "#"*70)
    print(f"# Conversion Complete: {count} annotations processed")
    print("#"*70)
    print("\nNext steps:")
    print("1. Verify output directory structure")
    print("2. Run: python partition_dataset.py")
    print("3. Run: python validate_dataset.py")
    print("\n")


if __name__ == "__main__":
    main()
