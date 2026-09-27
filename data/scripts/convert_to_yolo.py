#!/usr/bin/env python3
"""Convert the original LISA CSV / Bosch YAML annotations to independent YOLO datasets.

Raw files remain untouched. Images are hard-linked where possible and copied only
when the filesystem cannot link them.
"""
import argparse
import csv
import hashlib
import shutil
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


def output_name(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    digest = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:10]
    return f"{path.stem}_{digest}{path.suffix.lower()}"


def place_image(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return
    try:
        target.hardlink_to(source)
    except OSError:
        shutil.copy2(source, target)


def normalized_box(x1: float, y1: float, x2: float, y2: float, width: int, height: int) -> Optional[str]:
    x1, x2 = sorted((max(0.0, min(float(width), x1)), max(0.0, min(float(width), x2))))
    y1, y2 = sorted((max(0.0, min(float(height), y1)), max(0.0, min(float(height), y2))))
    if width <= 0 or height <= 0 or x2 <= x1 or y2 <= y1:
        return None
    return f"0 {(x1+x2)/(2*width):.6f} {(y1+y2)/(2*height):.6f} {(x2-x1)/width:.6f} {(y2-y1)/height:.6f}"


def image_dimensions(path: Path) -> Tuple[int, int]:
    try:
        from PIL import Image
        with Image.open(path) as image:
            return image.size
    except ImportError as exc:
        raise RuntimeError("Instala Pillow (pip install Pillow) para leer dimensiones de imagen.") from exc


def convert_lisa(root: Path, output: Path) -> int:
    images = {p.name: p for p in root.rglob("*.jpg") if "annotation" not in p.parts}
    grouped: Dict[Path, List[Tuple[float, float, float, float]]] = {}
    for csv_path in root.rglob("*.csv"):
        try:
            with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream, delimiter=";")
                required = {"Filename", "Upper left corner X", "Upper left corner Y", "Lower right corner X", "Lower right corner Y"}
                if not reader.fieldnames or not required.issubset(reader.fieldnames):
                    continue
                for row in reader:
                    image = images.get(Path(row["Filename"]).name)
                    if not image:
                        continue
                    try:
                        box = tuple(float(row[k]) for k in ("Upper left corner X", "Upper left corner Y", "Lower right corner X", "Lower right corner Y"))
                    except (TypeError, ValueError):
                        continue
                    grouped.setdefault(image, []).append(box)
        except UnicodeDecodeError:
            continue
    return write_yolo(root, output, grouped)


def convert_bosch(root: Path, output: Path) -> int:
    try:
        import yaml
    except ImportError:
        yaml = None
    image_map = {p.name: p for p in root.rglob("*.png")}
    annotation_file = root / "test.yaml"
    if yaml:
        with annotation_file.open(encoding="utf-8") as stream:
            records = yaml.safe_load(stream) or []
    else:
        # The distributed Bosch file uses a constrained YAML form: record blocks
        # with `- boxes:`, inline box mappings, and one `path:`. Parse only those
        # fields so conversion still works in a minimal Python installation.
        records = []
        text = annotation_file.read_text(encoding="utf-8")
        for block in re.split(r"(?m)^- boxes:", text)[1:]:
            path_match = re.search(r"(?m)^\s*path:\s*(.+?)\s*$", block)
            if not path_match:
                continue
            boxes = []
            for mapping in re.findall(r"\{([^{}]+)\}", block):
                fields = dict(re.findall(r"([A-Za-z_]+):\s*([^,]+)", mapping))
                if all(key in fields for key in ("x_min", "y_min", "x_max", "y_max")):
                    boxes.append(fields)
            records.append({"path": path_match.group(1).strip().strip("'\""), "boxes": boxes})
    grouped: Dict[Path, List[Tuple[float, float, float, float]]] = {}
    for record in records:
        image = image_map.get(Path(record.get("path", "")).name)
        if not image:
            continue
        for box in record.get("boxes", []) or []:
            try:
                grouped.setdefault(image, []).append(tuple(float(box[k]) for k in ("x_min", "y_min", "x_max", "y_max")))
            except (KeyError, TypeError, ValueError):
                continue
    return write_yolo(root, output, grouped)


def write_yolo(root: Path, output: Path, grouped: Dict[Path, List[Tuple[float, float, float, float]]]) -> int:
    image_dir, label_dir = output / "images", output / "labels"
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for image, boxes in grouped.items():
        width, height = image_dimensions(image)
        labels = [label for box in boxes if (label := normalized_box(*box, width, height))]
        if not labels:
            continue
        target_name = output_name(image, root)
        place_image(image, image_dir / target_name)
        (label_dir / f"{Path(target_name).stem}.txt").write_text("\n".join(labels) + "\n", encoding="utf-8")
        count += len(labels)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("lisa", "bosch"), required=True)
    parser.add_argument("--input", type=Path, required=True, help="Raíz original del dataset")
    parser.add_argument("--output", type=Path, required=True, help="Raíz derivada, p. ej. data/processed/lisa")
    args = parser.parse_args()
    if not args.input.is_dir():
        parser.error(f"No existe el dataset local: {args.input}")
    count = convert_lisa(args.input, args.output) if args.dataset == "lisa" else convert_bosch(args.input, args.output)
    print(f"{args.dataset}: {count} cajas convertidas en {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
