#!/usr/bin/env python3
"""
Generador de dataset aumentado de Bogotá para OptiSignal-AI.

A partir de las 15 imágenes reales de Bogotá:
1. Extrae y filtra cajas delimitadoras limpias de semáforos verticales.
2. Inyecta estados ópticos sintéticos fotorealistas (Rojo, Amarillo, Verde, Apagado, Doble luz).
3. Aplica variaciones de entorno urbano (Día, Nublado/Lluvia, Atardecer, Noche con farolas).
4. Aplica aumentos geométricos (volteo horizontal con inversión de cajas, cambios de escala).
5. Genera etiquetas YOLO correspondientes y particiona en train/val/test.
"""

import json
import random
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BOGOTA_REAL_DIR = ROOT / "data" / "datasets" / "bogota_real"
OUTPUT_DIR = ROOT / "data" / "datasets" / "bogota_augmented"
PROCESSED_DIR = ROOT / "data" / "processed" / "bogota_augmented" / "partitioned"

import sys
sys.path.insert(0, str(ROOT / "data" / "scripts"))
from partition_dataset import partition
from validate_dataset import validate_dataset


def clean_boxes(lines: List[str], w: int, h: int) -> List[Tuple[float, float, float, float]]:
    """Filtra y limpia cajas con NMS simple y regla de relación de aspecto vertical."""
    candidates = []
    for line in lines:
        parts = line.strip().split()
        if not parts:
            continue
        cx, cy, bw, bh = map(float, parts[1:])
        x1 = (cx - bw / 2) * w
        y1 = (cy - bh / 2) * h
        x2 = (cx + bw / 2) * w
        y2 = (cy + bh / 2) * h
        bw_px = x2 - x1
        bh_px = y2 - y1
        if bh_px > bw_px * 1.05 and bh_px >= 30:  # Semáforo vertical visible
            candidates.append((x1, y1, x2, y2, cx, cy, bw, bh))

    if not candidates:
        return []

    # Ordenar por altura descendente (los más prominentes primero)
    candidates.sort(key=lambda b: (b[3] - b[1]), reverse=True)
    kept = []
    for b in candidates:
        overlap = False
        for k in kept:
            ix1 = max(b[0], k[0])
            iy1 = max(b[1], k[1])
            ix2 = min(b[2], k[2])
            iy2 = min(b[3], k[3])
            inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
            area_b = (b[2] - b[0]) * (b[3] - b[1])
            if area_b > 0 and inter / area_b > 0.45:
                overlap = True
                break
        if not overlap:
            kept.append(b)

    return [(b[4], b[5], b[6], b[7]) for b in kept]


def draw_lens(img: np.ndarray, cx: int, cy: int, r: int, state: str, r_off: int = 0) -> None:
    """Dibuja una lente óptica realista en el semáforo con halo difuso y núcleo LED."""
    h_img, w_img = img.shape[:2]
    if r < 3 or cx < 0 or cx >= w_img or cy < 0 or cy >= h_img:
        return

    # Limpiar primero cualquier luz o brillo previo de la fotografía original
    blank_r = max(r, r_off)
    cv2.circle(img, (cx, cy), blank_r, (32, 32, 32), -1)
    cv2.circle(img, (cx, cy), max(1, int(blank_r * 0.85)), (42, 42, 42), -1)

    if state == "OFF":
        # Lente apagada: disco gris oscuro con bisel y textura sutil
        cv2.circle(img, (cx, cy), max(1, int(blank_r * 0.4)), (52, 52, 52), -1)
        return

    # Definir colores BGR según estado lumínico
    if state == "RED":
        halo_color = (10, 10, 180)
        core_color = (20, 25, 245)
        hotspot_color = (190, 190, 255)
    elif state == "YELLOW":
        halo_color = (0, 160, 210)
        core_color = (0, 215, 255)
        hotspot_color = (190, 245, 255)
    elif state == "GREEN":
        halo_color = (10, 170, 25)
        core_color = (25, 240, 55)
        hotspot_color = (190, 255, 210)
    else:
        return

    # Halo difuso transparente (bloom)
    overlay = img.copy()
    halo_r = int(r * 1.35)
    cv2.circle(overlay, (cx, cy), halo_r, halo_color, -1)
    cv2.addWeighted(overlay, 0.45, img, 0.55, 0, img)

    # Núcleo brillante LED
    cv2.circle(img, (cx, cy), r, core_color, -1)

    # Punto central incandescente
    hotspot_r = max(1, int(r * 0.45))
    cv2.circle(img, (cx, cy), hotspot_r, hotspot_color, -1)


def apply_optical_state(
    img: np.ndarray,
    boxes: List[Tuple[float, float, float, float]],
    state_name: str
) -> np.ndarray:
    """Aplica el estado óptico a los semáforos identificados en la imagen."""
    result = img.copy()
    h, w = result.shape[:2]

    for cx_norm, cy_norm, bw_norm, bh_norm in boxes:
        x1 = max(0, int((cx_norm - bw_norm / 2) * w))
        y1 = max(0, int((cy_norm - bh_norm / 2) * h))
        x2 = min(w, int((cx_norm + bw_norm / 2) * w))
        y2 = min(h, int((cy_norm + bh_norm / 2) * h))

        box_h = y2 - y1
        box_w = x2 - x1
        if box_h < 20 or box_w < 8:
            continue

        third_h = box_h // 3
        lens_r = max(2, int(min(third_h, box_w) * 0.32))
        r_off = max(3, int(min(third_h, box_w) * 0.44))
        lens_cx = x1 + box_w // 2

        cy_red = y1 + third_h // 2
        cy_yel = y1 + third_h + third_h // 2
        cy_grn = y1 + 2 * third_h + third_h // 2

        # Determinar estado de cada una de las 3 ópticas
        if state_name == "RED":
            s_red, s_yel, s_grn = "RED", "OFF", "OFF"
        elif state_name == "YELLOW":
            s_red, s_yel, s_grn = "OFF", "YELLOW", "OFF"
        elif state_name == "GREEN":
            s_red, s_yel, s_grn = "OFF", "OFF", "GREEN"
        elif state_name == "OFF":
            s_red, s_yel, s_grn = "OFF", "OFF", "OFF"
        elif state_name == "MULTIPLE_RED_YELLOW":
            s_red, s_yel, s_grn = "RED", "YELLOW", "OFF"
        elif state_name == "MULTIPLE_RED_GREEN":
            s_red, s_yel, s_grn = "RED", "OFF", "GREEN"
        else:
            s_red, s_yel, s_grn = "RED", "OFF", "OFF"

        draw_lens(result, lens_cx, cy_red, lens_r, s_red, r_off)
        draw_lens(result, lens_cx, cy_yel, lens_r, s_yel, r_off)
        draw_lens(result, lens_cx, cy_grn, lens_r, s_grn, r_off)

    return result


def apply_environment(img: np.ndarray, env_type: str) -> np.ndarray:
    """Aplica transformaciones de iluminación y clima urbano de Bogotá."""
    res = img.astype(np.float32)

    if env_type == "DAYLIGHT":
        # Ligero ajuste de contraste estándar
        res = res * 1.02
    elif env_type == "OVERCAST":
        # Tarde nublada/lluvia bogotana: menor saturación, tinte ligeramente frío
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] *= 0.80  # Desaturar 20%
        hsv[:, :, 2] *= 0.88  # Oscurecer ligeramente
        bgr = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
        bgr[:, :, 0] += 8.0   # Tinte azul/frío
        bgr[:, :, 2] -= 4.0   # Menos rojo
        res = bgr
    elif env_type == "DUSK":
        # Atardecer / Golden hour: cálido naranja
        res[:, :, 2] = res[:, :, 2] * 1.12 + 10  # Más rojo
        res[:, :, 1] = res[:, :, 1] * 1.03 + 4   # Verde suave
        res[:, :, 0] = res[:, :, 0] * 0.85       # Menos azul
    elif env_type == "NIGHT":
        # Noche urbana bogotana: atenuar fondo, preservar puntos de luz
        res = res * 0.40
        # Aumentar contraste para luces callejeras
        res = np.power(res / 255.0, 1.25) * 255.0

    return np.clip(res, 0, 255).astype(np.uint8)


def generate_dataset() -> Dict:
    """Genera el dataset aumentado completo a partir de las 15 imágenes base."""
    images_in = BOGOTA_REAL_DIR / "images"
    labels_in = BOGOTA_REAL_DIR / "labels"

    img_out = OUTPUT_DIR / "images"
    lbl_out = OUTPUT_DIR / "labels"
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)

    base_images = sorted(images_in.glob("*.jpg"))
    print(f"Iniciando aumento sobre {len(base_images)} imágenes base de Bogotá...")

    states = [
        "RED",
        "YELLOW",
        "GREEN",
        "OFF",
        "MULTIPLE_RED_YELLOW",
        "MULTIPLE_RED_GREEN",
    ]
    environments = ["DAYLIGHT", "OVERCAST", "DUSK", "NIGHT"]

    manifest = []
    count = 0

    for img_p in base_images:
        lbl_p = labels_in / (img_p.stem + ".txt")
        if not lbl_p.exists():
            continue

        raw_lines = lbl_p.read_text(encoding="utf-8").strip().splitlines()
        orig_img = cv2.imread(str(img_p))
        if orig_img is None:
            continue
        h, w = orig_img.shape[:2]

        boxes = clean_boxes(raw_lines, w, h)
        if not boxes:
            continue

        for state in states:
            for env in environments:
                # 1. Modificar ópticas y aplicar iluminación ambiental
                aug_img = apply_optical_state(orig_img, boxes, state)
                aug_img = apply_environment(aug_img, env)

                # Redimensionar si es excesivamente grande para acelerar el entrenamiento (max 1280px)
                max_dim = max(h, w)
                if max_dim > 1280:
                    scale = 1280.0 / max_dim
                    new_w, new_h = int(w * scale), int(h * scale)
                    aug_img = cv2.resize(aug_img, (new_w, new_h), interpolation=cv2.INTER_AREA)

                file_id = f"bogota_aug_{count:04d}_{img_p.stem}_{state.lower()}_{env.lower()}"
                out_img_path = img_out / f"{file_id}.jpg"
                out_lbl_path = lbl_out / f"{file_id}.txt"

                # Guardar imagen JPEG con calidad 92
                cv2.imwrite(str(out_img_path), aug_img, [cv2.IMWRITE_JPEG_QUALITY, 92])

                # Guardar etiquetas YOLO (class_id 0 para traffic_light)
                label_lines = [f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n" for cx, cy, bw, bh in boxes]
                out_lbl_path.write_text("".join(label_lines), encoding="utf-8")

                manifest.append({
                    "id": file_id,
                    "base_image": img_p.name,
                    "state": state,
                    "environment": env,
                    "boxes_count": len(boxes),
                    "flipped": False,
                })
                count += 1

                # 2. Volteo horizontal para la mitad de los casos (variación geométrica)
                if env in ("DAYLIGHT", "NIGHT") and state in ("RED", "GREEN", "OFF"):
                    flip_img = cv2.flip(aug_img, 1)
                    flip_boxes = [(1.0 - cx, cy, bw, bh) for cx, cy, bw, bh in boxes]

                    flip_id = f"{file_id}_flip"
                    cv2.imwrite(str(img_out / f"{flip_id}.jpg"), flip_img, [cv2.IMWRITE_JPEG_QUALITY, 92])

                    flip_label_lines = [f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n" for cx, cy, bw, bh in flip_boxes]
                    (lbl_out / f"{flip_id}.txt").write_text("".join(flip_label_lines), encoding="utf-8")

                    manifest.append({
                        "id": flip_id,
                        "base_image": img_p.name,
                        "state": state,
                        "environment": env,
                        "boxes_count": len(flip_boxes),
                        "flipped": True,
                    })
                    count += 1

    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generación completada: {count} imágenes aumentadas en {OUTPUT_DIR}")

    # Partición 70% train / 20% val / 10% test
    print("Particionando dataset...")
    partition_res = partition(OUTPUT_DIR, PROCESSED_DIR, ratios=(0.7, 0.2, 0.1), seed=42)
    print("Validando dataset particionado...")
    val_report = validate_dataset(str(PROCESSED_DIR))
    print(f"Estado de validación: {val_report['status']}")

    return {
        "total_generated": count,
        "partition": partition_res,
        "validation": val_report,
    }


if __name__ == "__main__":
    generate_dataset()
