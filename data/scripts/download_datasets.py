#!/usr/bin/env python3
"""Resolve local LISA/Bosch datasets first; fetch the shared Drive folder only if needed."""

import argparse
import shutil
import tempfile
from pathlib import Path
from typing import Dict

DRIVE_URL = "https://drive.google.com/drive/folders/1_Q2jS-ZgivHq8bc2KpVxw58tIeP60f5x?usp=sharing"


def is_lisa(root: Path) -> bool:
    return root.is_dir() and any(root.rglob("*.csv")) and any(root.rglob("*.jpg"))


def is_bosch(root: Path) -> bool:
    return root.is_dir() and (root / "test.yaml").is_file() and any(root.rglob("*.png"))


def resolve_datasets(data_root: Path, source_url: str = DRIVE_URL) -> Dict[str, Path]:
    """Return native roots. Existing valid datasets are never downloaded or overwritten."""
    validators = {"lisa": is_lisa, "bosch": is_bosch}
    roots = {name: data_root / name for name in validators}
    missing = [name for name, root in roots.items() if not validators[name](root)]
    if not missing:
        print("LISA y Bosch disponibles localmente; no se descargan.")
        return roots
    occupied = [name for name in missing if roots[name].exists()]
    if occupied:
        raise RuntimeError(
            f"Hay carpetas locales incompletas para {', '.join(occupied)}. No se sobrescribirán; corrige o mueve esas carpetas antes de continuar."
        )

    try:
        import gdown
    except ImportError as exc:
        raise RuntimeError(
            f"Faltan datasets locales ({', '.join(missing)}). Instala gdown para obtenerlos de Google Drive."
        ) from exc

    data_root.mkdir(parents=True, exist_ok=True)
    print(f"Faltan {', '.join(missing)}; descargando Google Drive a una carpeta temporal.")
    with tempfile.TemporaryDirectory(prefix="optisignal-datasets-") as temporary:
        result = gdown.download_folder(url=source_url, output=temporary, quiet=False, remaining_ok=True)
        if not result:
            raise RuntimeError("Google Drive no devolvió archivos. Comprueba que la carpeta sea accesible y conserva su estructura esperada.")
        invalid = [name for name in missing if not validators[name](Path(temporary) / name)]
        if invalid:
            raise RuntimeError(f"La descarga no produjo la estructura esperada para: {', '.join(invalid)}")
        for name in missing:
            shutil.copytree(Path(temporary) / name, roots[name])
    return roots


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path(__file__).resolve().parents[1] / "datasets")
    parser.add_argument("--drive-url", default=DRIVE_URL)
    args = parser.parse_args()
    roots = resolve_datasets(args.data_root, args.drive_url)
    for name, path in roots.items():
        print(f"{name}: {path} ({'disponible' if (is_lisa if name == 'lisa' else is_bosch)(path) else 'no disponible'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
