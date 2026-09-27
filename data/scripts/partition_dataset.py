#!/usr/bin/env python3
"""Create reproducible, per-dataset YOLO splits without modifying raw files."""
import argparse
import json
import random
import shutil
from pathlib import Path


def place(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.hardlink_to(source)
    except OSError:
        shutil.copy2(source, target)


def partition(input_dir: Path, output_dir: Path, ratios=(0.7, 0.2, 0.1), seed=42) -> dict:
    if any(r < 0 for r in ratios) or abs(sum(ratios) - 1.0) > 1e-8:
        raise ValueError("Las proporciones train/val/test deben sumar 1.")
    images_dir, labels_dir = input_dir / "images", input_dir / "labels"
    images = sorted(p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if not images:
        raise ValueError(f"No hay imágenes anotadas en {images_dir}")
    random.Random(seed).shuffle(images)
    n = len(images)
    n_train, n_val = int(n * ratios[0]), int(n * ratios[1])
    buckets = {"train": images[:n_train], "val": images[n_train:n_train+n_val], "test": images[n_train+n_val:]}
    for split, members in buckets.items():
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)
        for image in members:
            label = labels_dir / f"{image.stem}.txt"
            if not label.is_file():
                raise ValueError(f"Falta etiqueta para {image.name}: {label}")
            place(image, output_dir / "images" / split / image.name)
            place(label, output_dir / "labels" / split / label.name)
    dataset_name = input_dir.parent.name if input_dir.name.lower() == "yolo" else input_dir.name
    manifest = {"dataset": dataset_name, "seed": seed, "ratios": dict(zip(("train", "val", "test"), ratios)), "counts": {k: len(v) for k, v in buckets.items()}, "total_images": n}
    (output_dir / "partition_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "data.yaml").write_text(f"path: {output_dir.resolve().as_posix()}\ntrain: images/train\nval: images/val\ntest: images/test\nnc: 1\nnames: [traffic_light]\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Carpeta YOLO plana con images/ y labels/")
    parser.add_argument("--output", type=Path, required=True, help="Destino independiente de este dataset")
    parser.add_argument("--train", type=float, default=.7)
    parser.add_argument("--val", type=float, default=.2)
    parser.add_argument("--test", type=float, default=.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(partition(args.input, args.output, (args.train, args.val, args.test), args.seed), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
