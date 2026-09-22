#!/usr/bin/env python3
"""
Validate traffic light dataset integrity and format.

Usage:
    python validate_dataset.py --input ../datasets/combined/ --output ../datasets/validation_report.txt
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Tuple


def validate_yolo_format(label_file: Path) -> Tuple[bool, str]:
    """
    Validate YOLO format label file.
    """
    try:
        with open(label_file, "r") as f:
            lines = f.readlines()
        
        if not lines:
            return False, "Empty label file"
        
        for line_num, line in enumerate(lines, 1):
            parts = line.strip().split()
            
            if len(parts) != 5:
                return False, f"Line {line_num}: Expected 5 values, got {len(parts)}"
            
            try:
                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
                
                # Check class ID
                if class_id != 0:
                    return False, f"Line {line_num}: Invalid class_id {class_id}"
                
                # Check normalized coordinates
                for i, val in enumerate([x_center, y_center, width, height], 1):
                    if not (0 <= val <= 1):
                        return False, f"Line {line_num}: Value {val} not in range [0, 1]"
            
            except ValueError as e:
                return False, f"Line {line_num}: Invalid number format - {e}"
        
        return True, "Valid"
    
    except Exception as e:
        return False, f"Error reading file: {e}"


def validate_dataset(input_dir: str, output_file: str = None) -> Dict:
    """
    Validate entire dataset.
    """
    print(f"\nValidating dataset: {input_dir}")
    
    input_path = Path(input_dir)
    report = {
        "status": "PASS",
        "errors": [],
        "warnings": [],
        "statistics": {
            "total_images": 0,
            "total_labels": 0,
            "missing_labels": 0,
            "invalid_labels": 0,
            "split_distribution": {}
        }
    }
    
    # Check directory structure
    required_dirs = [
        "images/train", "images/val", "images/test",
        "labels/train", "labels/val", "labels/test"
    ]
    
    for dir_name in required_dirs:
        dir_path = input_path / dir_name
        if not dir_path.exists():
            report["errors"].append(f"Missing directory: {dir_name}")
            report["status"] = "FAIL"
    
    # Validate images and labels
    for split in ["train", "val", "test"]:
        images_dir = input_path / "images" / split
        labels_dir = input_path / "labels" / split
        
        if not images_dir.exists():
            continue
        
        image_files = list(images_dir.glob("*.[jp][pn]g"))
        report["statistics"]["total_images"] += len(image_files)
        report["statistics"]["split_distribution"][split] = len(image_files)
        
        print(f"\n[{split.upper()}] Validating {len(image_files)} images...")
        
        for img_file in image_files:
            label_file = labels_dir / (img_file.stem + ".txt")
            
            if not label_file.exists():
                report["statistics"]["missing_labels"] += 1
                report["warnings"].append(f"Missing label: {img_file.name}")
            else:
                report["statistics"]["total_labels"] += 1
                is_valid, msg = validate_yolo_format(label_file)
                
                if not is_valid:
                    report["statistics"]["invalid_labels"] += 1
                    report["errors"].append(f"Invalid label {label_file.name}: {msg}")
                    report["status"] = "FAIL"
    
    # Print report
    print("\n" + "="*70)
    print("VALIDATION REPORT")
    print("="*70)
    print(f"\nStatus: {report['status']}")
    print(f"\nStatistics:")
    print(f"  Total images: {report['statistics']['total_images']}")
    print(f"  Total labels: {report['statistics']['total_labels']}")
    print(f"  Missing labels: {report['statistics']['missing_labels']}")
    print(f"  Invalid labels: {report['statistics']['invalid_labels']}")
    
    if report['statistics']['split_distribution']:
        print(f"\nSplit Distribution:")
        for split, count in report['statistics']['split_distribution'].items():
            print(f"  {split}: {count} images")
    
    if report['errors']:
        print(f"\nErrors ({len(report['errors'])})")
        for error in report['errors'][:10]:
            print(f"  - {error}")
        if len(report['errors']) > 10:
            print(f"  ... and {len(report['errors']) - 10} more")
    
    if report['warnings']:
        print(f"\nWarnings ({len(report['warnings'])})")
        for warning in report['warnings'][:10]:
            print(f"  - {warning}")
        if len(report['warnings']) > 10:
            print(f"  ... and {len(report['warnings']) - 10} more")
    
    print("\n" + "="*70)
    
    # Save report to file
    if output_file:
        with open(output_file, "w") as f:
            f.write("VALIDATION REPORT\n")
            f.write("="*70 + "\n\n")
            f.write(f"Status: {report['status']}\n\n")
            f.write(json.dumps(report, indent=2))
        print(f"\nReport saved to: {output_file}")
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Validate traffic light dataset integrity and format"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Input dataset directory"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for validation report"
    )
    
    args = parser.parse_args()
    
    print("\n" + "#"*70)
    print("# OptiSignal-AI Dataset Validation Tool")
    print("#"*70)
    
    report = validate_dataset(args.input, args.output)
    
    print("\n" + "#"*70)
    if report["status"] == "PASS":
        print("# Validation PASSED")
    else:
        print("# Validation FAILED")
    print("#"*70)
    print("\nNext steps:")
    if report["status"] == "PASS":
        print("1. Dataset is ready for YOLO training")
        print("2. Proceed to Phase 4: YOLO Detector Training")
    else:
        print("1. Fix errors listed above")
        print("2. Re-run validation")
    print("\n")
    
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    exit(main())
