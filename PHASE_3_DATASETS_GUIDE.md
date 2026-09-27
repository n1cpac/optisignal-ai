# Fase 3 — Datasets de referencia

## Fuentes y estructura observada

El proyecto usa exclusivamente **LISA** y **Bosch Small Traffic Lights Dataset (BSTLD)**, almacenados de forma independiente. La descarga existente de LISA contiene secuencias en carpetas como `dayTrain`, `daySequence1`, `nightTrain` y CSV en `Annotations/Annotations`. Bosch contiene imágenes en `rgb/test` y anotaciones en `test.yaml`; las rutas de ese YAML apuntan a un servidor externo, por lo que el conversor las resuelve usando el nombre de archivo local.

No se reorganiza ni modifica la raw data. La estructura recomendada es:

```text
data/
├── datasets/                 # originales descargados; ignorados por Git
│   ├── lisa/                 # estructura nativa LISA intacta
│   └── bosch/                # estructura nativa BSTLD intacta
└── processed/                # artefactos derivados; ignorados por Git
    ├── lisa/
    │   ├── yolo/             # images/ y labels/ planos
    │   └── partitioned/      # images/{train,val,test}, labels/{train,val,test}
    └── bosch/
        ├── yolo/
        └── partitioned/
```

Las imágenes derivadas se enlazan con hard links cuando el sistema de archivos lo permite; en otros casos se copian. Cada fuente conserva su propio conjunto y partición; no se fusionan ni se mezclan.

## Disponibilidad de datos

El resolvedor local-first no vuelve a descargar un dataset que ya está presente. Si falta LISA o Bosch, obtiene la carpeta compartida indicada desde `download_datasets.py`; necesita `gdown`. La carpeta compartida debe exponer los directorios `lisa/` y `bosch/` con sus estructuras nativas.

```powershell
python data/scripts/download_datasets.py
```

Se puede cambiar la raíz local o el enlace con `--data-root` y `--drive-url`. Si no están disponibles los datos locales ni la dependencia `gdown`, el script informa el requisito y termina con error.

## Preparación y partición

Instala `Pillow`, `PyYAML` y `gdown` (ver `data/requirements_data.txt`). El entrypoint ejecuta detección local-first, descarga faltantes, conversión, partición y validación por cada fuente:

```powershell
python data/scripts/prepare_datasets.py
```

Para trabajar por separado, los comandos `convert_to_yolo.py`, `partition_dataset.py` y `validate_dataset.py` aceptan rutas explícitas; consulta `--help` en cada script.

El conversor usa las cajas anotadas por cada fuente y normaliza sus coordenadas al formato YOLO de una clase (`traffic_light`). Por tanto, las anotaciones corresponden a instancias de luz/caja de origen y no inventan cajas de cabezal agrupando lentes. La división es reproducible por semilla (70/20/10 por defecto) y produce `data.yaml` y un manifiesto para cada dataset.

La cantidad final de ejemplos depende de la versión descargada, de las imágenes locales disponibles y de las anotaciones que referencien esas imágenes. No se asumen conteos de catálogo como conteos de salida.

## Resultado y etapa siguiente

La Fase 3 queda lista cuando ambos datasets producen particiones YOLO válidas, independientes y con manifiestos. La configuración `data.yaml` de LISA o Bosch se puede entregar directamente al entrenamiento de la Fase 4. La Fase 2 (prototipo físico) permanece independiente y puede implementarse después.
