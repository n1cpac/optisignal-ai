#!/usr/bin/env python3
"""Resolve source datasets then convert, partition and validate each independently."""
import argparse
from pathlib import Path

from convert_to_yolo import convert_bosch, convert_lisa
from download_datasets import DRIVE_URL, resolve_datasets
from partition_dataset import partition
from validate_dataset import validate_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path(__file__).resolve().parents[1] / "datasets")
    parser.add_argument("--processed-root", type=Path, default=Path(__file__).resolve().parents[1] / "processed")
    parser.add_argument("--drive-url", default=DRIVE_URL)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    roots = resolve_datasets(args.data_root, args.drive_url)
    for name, source in roots.items():
        destination = args.processed_root / name
        yolo = destination / "yolo"
        partitioned = destination / "partitioned"
        count = convert_lisa(source, yolo) if name == "lisa" else convert_bosch(source, yolo)
        if count == 0:
            raise RuntimeError(f"No se encontraron cajas anotadas para {name}; revisa nombres/rutas de la fuente.")
        manifest = partition(yolo, partitioned, seed=args.seed)
        report = validate_dataset(str(partitioned))
        if report["status"] != "PASS":
            raise RuntimeError(f"La validación de {name} falló; revisa {partitioned}.")
        print(f"{name}: {count} cajas, {manifest['total_images']} imágenes. Listo en {partitioned}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
