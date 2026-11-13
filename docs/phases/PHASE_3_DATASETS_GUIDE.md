# Fase 3 — Datasets de referencia y datos reales de Bogotá

## 1. Primera etapa: Datasets públicos base (LISA y Bosch)

Inicialmente, la preparación de datos se estructuró sobre dos repositorios abiertos independientes:

- **LISA Traffic Light Dataset:** secuencias diurnas y nocturnas (`36,775` imágenes procesadas, `232,348` cajas) divididas en `25,742 train` / `7,355 val` / `3,678 test`.
- **Bosch Small Traffic Lights Dataset (BSTLD):** imágenes de semáforos pequeños (`7,147` imágenes procesadas, `13,486` cajas) divididas en `5,002 train` / `1,429 val` / `716 test`.

Ambos fueron convertidos a anotación YOLO de clase única (`traffic_light`) con partición reproducible 70/20/10 (`seed=42`) bajo `data/processed/lisa/` y `data/processed/bosch/`, logrando validación limpia (`0` etiquetas ausentes o inválidas). También se exploraron renders sintéticos en `data/processed/blender/`.

---

## 2. Limitación observada y cambio metodológico

Aunque LISA, Bosch y Blender permitieron validar el flujo de conversión y entrenar los primeros pesos separados (`lisa_best.pt`, `bosch_best.pt`, `blender_best.pt`), al llevarlos a cámaras urbanas de Bogotá aparecieron limitaciones claras:

- Baja tasa de acierto en pórticos altos, postes amarillos con visera pronunciada y cámaras nocturnas locales.
- Usar tres modelos en ensamble saturaba la CPU (~2 FPS), generando desfase severo frente al video.
- Se descartó además el banco de laboratorio físico (ESP32), por lo que era imprescindible entrenar y validar directamente sobre el dominio visual bogotano.

---

## 3. Segunda etapa: Dataset `bogota_augmented` y videos CCTV (`s1`–`s8`)

Para resolver la brecha de dominio se construyó el conjunto unificado **`data/processed/bogota_augmented/partitioned/`**:

```text
data/
├── processed/
│   ├── lisa/partitioned/              # 36,775 imágenes (referencia base)
│   ├── bosch/partitioned/             #  7,147 imágenes (referencia base)
│   ├── blender/                       # Referencia sintética previa
│   └── bogota_augmented/partitioned/  # Dataset definitivo de Bogotá
│       ├── images/{train,val,test}    # 315 / 90 / 45 imágenes (total: 450)
│       ├── labels/{train,val,test}    # Clase única: traffic_light (nc: 1)
│       ├── data.yaml
│       └── partition_manifest.json    # seed=42, split 70/20/10
├── test_videos/                       # 8 secuencias reales de Bogotá a 15 FPS
│   ├── cctv_s1.mp4  (AK 80 con AC 55 S — parpadeo amarillo nocturno)
│   ├── cctv_s2.mp4  (CL 17 con KR 106 — apagón total)
│   ├── cctv_s3.mp4  (KR 92 con CL 169B — 2 cabezales en verde)
│   ├── cctv_s4.mp4  (AC 26 con KR 19 — cabezales pequeños/lejanos)
│   ├── cctv_s5.mp4  (KR 14 con CL 44 S — pórtico 3 amarillo intermitente + paneo)
│   ├── cctv_s6.mp4  (AK 7 con CL 84 — verde con peatón cercano)
│   ├── cctv_s7.mp4  (AK 104 con AC 145 — rojo multi-cabezal con movimiento)
│   └── cctv_s8.mp4  (AK 104 con AC 72 — transición amarillo -> rojo en pórtico)
└── history_scenes/
    └── escena_s1.png ... escena_s8.png  # Captura específica de cada cruce para Historial
```

### Auditoría y limpieza de datos
Durante la optimización del repositorio se eliminaron copias crudas redundantes y assets pesados que no intervenían en ejecución ni en pruebas, conservando únicamente los derivados necesarios en `data/processed/`, los 8 videos de validación en `data/test_videos/` y las 8 escenas de historial en `data/history_scenes/`.

---

## 4. Resultado

Los datos de `bogota_augmented` alimentaron el entrenamiento del modelo unificado `models/optisignal_best.pt` (Fase 4), mientras `cctv_s1.mp4`–`cctv_s8.mp4` constituyen la suite de regresión y demostración del sistema en vivo.
