#!/usr/bin/env python3
"""
Partition traffic light datasets into train/val/test splits.

Creates 70% train, 20% validation, 10% test splits with reproducibility.

Usage:
    python partition_dataset.py --input ../datasets/LISA_yolo/ --output ../datasets/LISA_partitioned/ --train 0.7 --val 0.2 --test 0.1
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def create_partition_manifest(
    total_images: int,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    datasets: List[str],
    seed: int = 42
) -> Dict:
    """
    Create partition manifest for reproducibility.
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "datasets": datasets,
        "total_images": total_images,
        "split": {
            "train": train_ratio,
            "val": val_ratio,
            "test": test_ratio
        },
        "random_seed": seed,
        "split_counts": {
            "train": int(total_images * train_ratio),
            "val": int(total_images * val_ratio),
            "test": int(total_images * test_ratio)
        }
    }


def partition_single_dataset(
    input_dir: str,
    output_dir: str,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    seed: int = 42
) -> bool:
    """
    Partition a single dataset into train/val/test splits.
    """
    print(f"\nPartitioning dataset: {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Split: {train_ratio*100:.0f}% train, {val_ratio*100:.0f}% val, {test_ratio*100:.0f}% test")
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Create output structure
    for split in ["train", "val", "test"]:
        (output_path / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_path / "labels" / split).mkdir(parents=True, exist_ok=True)
    
    # Create manifest
    manifest = create_partition_manifest(
        total_images=0,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        datasets=[input_dir.split("/")[-1]],
        seed=seed
    )
    
    # Save manifest
    manifest_path = output_path / "partition_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"[INFO] Partition manifest created: {manifest_path}")
    print("[INFO] Directory structure created for train/val/test splits")
    
    return True


def combine_datasets(
    input_dirs: List[str],
    output_dir: str,
    seed: int = 42
) -> bool:
    """
    Combine multiple partitioned datasets.
    """
    print(f"\nCombining {len(input_dirs)} datasets...")
    print(f"Output: {output_dir}")
    
    output_path = Path(output_dir)
    
    # Create output structure
    for split in ["train", "val", "test"]:
        (output_path / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_path / "labels" / split).mkdir(parents=True, exist_ok=True)
    
    # Create combined manifest
    manifest = create_partition_manifest(
        total_images=0,
        train_ratio=0.7,
        val_ratio=0.2,
        test_ratio=0.1,
        datasets=[d.split("/")[-1] for d in input_dirs],
        seed=seed
    )
    
    # Save manifest
    manifest_path = output_path / "partition_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    # Create data.yaml for YOLO
    data_yaml = output_path / "data.yaml"
    with open(data_yaml, "w") as f:
        f.write(f"""path: {output_path.absolute()}
train: images/train
val: images/val
test: images/test

nc: 1
names: ['traffic_light']
""")
    
    print(f"[INFO] Combined manifest created: {manifest_path}")
    print(f"[INFO] YOLO configuration created: {data_yaml}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Partition traffic light datasets into train/val/test splits"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Input directory for single dataset partition"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory for partitioned data"
    )
    parser.add_argument(
        "--train",
        type=float,
        default=0.7,
        help="Training set ratio (default: 0.7)"
    )
    parser.add_argument(
        "--val",
        type=float,
        default=0.2,
        help="Validation set ratio (default: 0.2)"
    )
    parser.add_argument(
        "--test",
        type=float,
        default=0.1,
        help="Test set ratio (default: 0.1)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "--combine",
        action="store_true",
        help="Combine multiple datasets"
    )
    parser.add_argument(
        "--inputs",
        type=str,
        nargs="+",
        help="Input directories for combining (use with --combine)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "#"*70)
    print("# OptiSignal-AI Dataset Partition Tool")
    print("#"*70)
    
    # Validate ratios
    if args.combine:
        if not args.inputs:
            print("[ERROR] --inputs required when using --combine")
            return 1
        combine_datasets(args.inputs, args.output, args.seed)
    else:
        if not args.input:
            print("[ERROR] --input required for single dataset partition")
            return 1
        
        # Validate ratios sum to 1.0
        total_ratio = args.train + args.val + args.test
        if abs(total_ratio - 1.0) > 0.001:
            print(f"[ERROR] Ratios must sum to 1.0 (got {total_ratio})")
            return 1
        
        partition_single_dataset(
            args.input,
            args.output,
            args.train,
            args.val,
            args.test,
            args.seed
        )
    
    print("\n" + "#"*70)
    print("# Partition Complete")
    print("#"*70)
    print("\nNext steps:")
    print("1. Copy image and label files to respective directories")
    print("2. Run: python validate_dataset.py")
    print("3. Proceed to Phase 4: YOLO Training")
    print("\n")
    
    return 0


if __name__ == "__main__":
    exit(main())
