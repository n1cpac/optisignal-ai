# Carga CONFIG_PARAMETERS.yaml, la unica fuente de parametros del sistema
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

with open(ROOT / "CONFIG_PARAMETERS.yaml", encoding="utf-8") as f:
    SETTINGS = yaml.safe_load(f)
