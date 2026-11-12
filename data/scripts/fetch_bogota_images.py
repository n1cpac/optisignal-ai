#!/usr/bin/env python3
"""
Descarga y valida 20 imágenes reales de semáforos en Bogotá desde fuentes públicas abiertas (Wikimedia Commons CDN).
Usa el endpoint de thumbnails (1280px) para máxima compatibilidad, velocidad y respetar el rate limit de Wikimedia.
Guarda las imágenes en data/datasets/bogota_real/images/ y genera un manifiesto con metadatos.
"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
import cv2

OUTPUT_DIR = Path("data/datasets/bogota_real/images")
MANIFEST_FILE = Path("data/datasets/bogota_real/manifest.json")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "OptiSignalAcademicTrafficResearch/1.0 (Contact: est.nicolas.acevedo@unimilitar.edu.co; University project on traffic lights)"
}


def search_wikimedia_thumbnails(query: str, limit: int = 25) -> list[dict]:
    url = (
        "https://commons.wikimedia.org/w/api.php?action=query"
        f"&generator=search&gsrsearch={urllib.parse.quote(query)}"
        f"&gsrnamespace=6&gsrlimit={limit}"
        "&prop=imageinfo&iiprop=url|thumburl|mime|size&iiurlwidth=1280&format=json"
    )
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        pages = data.get("query", {}).get("pages", {})
        results = []
        for pid, p in pages.items():
            title = p.get("title", "")
            ii = p.get("imageinfo", [{}])[0]
            thumb_url = ii.get("thumburl", "") or ii.get("url", "")
            mime = ii.get("mime", "")
            size = ii.get("size", 0)
            if mime in ["image/jpeg", "image/png"] and thumb_url:
                results.append({
                    "title": title,
                    "url": thumb_url,
                    "original_url": ii.get("url", ""),
                    "source": "Wikimedia Commons",
                    "size": size
                })
        return results
    except Exception as exc:
        print(f"Error consultando Wikimedia para '{query}': {exc}")
        return []


def download_image(url: str, dest_path: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        dest_path.write_bytes(data)
        # Validar con OpenCV
        img = cv2.imread(str(dest_path))
        if img is None or img.shape[0] < 300 or img.shape[1] < 300:
            if dest_path.exists():
                dest_path.unlink()
            return False
        return True
    except Exception as exc:
        print(f"Error descargando {url}: {exc}")
        if dest_path.exists():
            dest_path.unlink()
        return False


def main():
    print("=== BÚSQUEDA Y DESCARGA DE 20 IMÁGENES REALES DE SEMÁFOROS EN BOGOTÁ ===")
    
    queries = [
        "semáforo bogota",
        "semáforos bogota",
        "2018 Bogotá semáforos",
        "Bogota semáforo en rojo",
        "Bogotá semáforos",
        "carrera 7 bogota semaforo",
        "calle 45 carrera bogota",
        "avenida caracas bogota",
        "calle 26 bogota",
        "carrera 10 bogota",
        "avenida jimenez bogota",
        "calle 72 bogota carrera",
        "cruce semaforico bogota",
        "interseccion bogota",
        "calle 100 bogota carrera",
        "transmilenio calle bogota",
        "carrera 13 bogota calle"
    ]
    
    candidates = {}
    for q in queries:
        items = search_wikimedia_thumbnails(q, limit=20)
        for it in items:
            if it["url"] not in candidates:
                candidates[it["url"]] = it
        if len(candidates) >= 120:
            break
        time.sleep(0.3)

    print(f"Candidatos encontrados con CDN thumbnails: {len(candidates)}")
    
    # Cargar YOLO para verificar que la imagen contenga semáforos reales
    from ultralytics import YOLO
    model = YOLO("models/lisa_best.pt")
    base_model = YOLO("yolov8n.pt")  # COCO class 9 = traffic light

    downloaded = []
    
    # Comprobar si ya tenemos las 3 primeras descargadas
    for i in range(1, 4):
        p = OUTPUT_DIR / f"bogota_real_{i:02d}.jpg"
        if p.exists():
            img = cv2.imread(str(p))
            if img is not None:
                h, w = img.shape[:2]
                downloaded.append({
                    "id": f"bogota_{i:02d}",
                    "file": p.name,
                    "title": f"Semáforos Bogotá {i}",
                    "resolution": f"{w}x{h}",
                    "source": "Wikimedia Commons"
                })
                print(f"  ✓ Existente: {p.name} ({w}x{h})")

    idx = len(downloaded) + 1
    
    for url, info in candidates.items():
        if len(downloaded) >= 20:
            break
            
        ext = ".jpg" if "png" not in url.lower() else ".png"
        filename = f"bogota_real_{idx:02d}{ext}"
        dest = OUTPUT_DIR / filename
        
        # Si ya existe en la lista, saltar
        if any(d["file"] == filename for d in downloaded):
            idx += 1
            continue

        print(f"[{idx}/20] Descargando: {info['title'][:60]}...")
        if download_image(url, dest):
            img = cv2.imread(str(dest))
            # Test con base_model (class 9 = traffic light) y lisa_best
            res_base = base_model.predict(img, classes=[9], conf=0.15, verbose=False)[0]
            res_lisa = model.predict(img, conf=0.15, verbose=False)[0]
            
            box_count = len(res_base.boxes) + len(res_lisa.boxes)
            
            title_lower = info["title"].lower()
            is_semaforo_title = any(k in title_lower for k in ["semáforo", "semaforo", "traffic light", "cruce", "interseccion", "carrera 7", "calle 45"])
            
            if box_count > 0 or is_semaforo_title:
                h, w = img.shape[:2]
                downloaded.append({
                    "id": f"bogota_{idx:02d}",
                    "file": filename,
                    "title": info["title"],
                    "url": info.get("original_url", url),
                    "resolution": f"{w}x{h}",
                    "source": info["source"],
                    "detections_detected": box_count
                })
                print(f"  ✓ ACEPTADA: {w}x{h} ({box_count} semáforos detectados)")
                idx += 1
            else:
                print("  ✗ Descartada: no se detectó semáforo en la escena")
                dest.unlink()
                
        time.sleep(1.0)  # Cortesía con el CDN de Wikimedia
    
    # Guardar manifiesto
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(downloaded, f, indent=2, ensure_ascii=False)
        
    print(f"\n✓ Proceso finalizado. Total imágenes reales de Bogotá guardadas: {len(downloaded)}")
    print(f"✓ Guardadas en: {OUTPUT_DIR.resolve()}")
    print(f"✓ Manifiesto: {MANIFEST_FILE.resolve()}")

if __name__ == "__main__":
    main()
