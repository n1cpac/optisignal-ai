# Ubica un semaforo en el cruce de dos vias a partir de los nombres de la Malla Vial de Bogota
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

# Como se escribe cada tipo de via en la Malla Vial (MVIETIQUET)
PALABRAS = [
    ("AVENIDA CALLE", "AC"), ("AVENIDA CARRERA", "AK"), ("CALLE", "CL"), ("CARRERA", "KR"),
    ("TRANSVERSAL", "TV"), ("DIAGONAL", "DG"), ("SUR", "S"), ("ESTE", "E"),
]
# Si una via no aparece con su tipo, se prueba el equivalente (la CL 72 suele estar como AC 72)
EQUIVALENTES = {"AC": "CL", "CL": "AC", "AK": "KR", "KR": "AK"}
METROS_POR_GRADO = 111_000
MAX_SEPARACION_M = 30  # vias que no comparten vertice: deben pasar al menos asi de cerca
# Puntos de contacto a menos de esto son el mismo cruce (el intercambiador de la AK 68 con la AC 26 abarca 350 m);
# si quedan grupos separados, las vias se cruzan en varios sitios
MISMO_CRUCE_M = 400


def normalizar(via: str) -> str:
    """'Calle 72' -> 'CL 72'. No se cambian las letras pegadas: 'KR 13' y 'KR 13 E' son vias distintas."""
    via = " ".join(via.upper().split())
    for largo, corto in PALABRAS:
        via = re.sub(rf"\b{largo}\b", corto, via)
    return via


class MallaVial:
    """Vertices de cada via (por etiqueta) para encontrar donde se cruzan dos vias."""

    def __init__(self, ruta: Path):
        with open(ruta, encoding="utf-8") as f:
            features = json.load(f)["features"]
        self.vertices: dict[str, set[tuple[float, float]]] = defaultdict(set)
        for feature in features:
            etiqueta = feature["properties"].get("etiqueta")
            if not etiqueta:
                continue
            geometria = feature["geometry"]
            lineas = [geometria["coordinates"]] if geometria["type"] == "LineString" else geometria["coordinates"]
            for linea in lineas:
                self.vertices[etiqueta].update(tuple(punto) for punto in linea)

    def cruce(self, nombre: str) -> tuple[float, float]:
        """(lat, lng) del cruce de 'AC 72 con KR 13'."""
        partes = re.split(r"\s+CON\s+", normalizar(nombre))
        if len(partes) != 2:
            raise ValueError(f"'{nombre}': se esperaban dos vias separadas por 'con', ej. 'AC 72 con KR 13'")
        opciones_a, opciones_b = (self._opciones(parte, nombre) for parte in partes)

        # Primero los nombres tal cual; si no se cruzan, sus equivalentes. Ej.: 'CL 26' existe en el
        # centro, pero la que cruza la AK 68 es la 'AC 26' (El Dorado)
        for a in opciones_a:
            for b in opciones_b:
                contacto = self._contacto(a, b)
                if contacto is not None:
                    return self._centro(contacto, nombre)
        raise ValueError(f"'{nombre}': las vias no se cruzan en la Malla Vial")

    def _opciones(self, via: str, nombre: str) -> list[set[tuple[float, float]]]:
        tipo, _, resto = via.partition(" ")
        candidatas = [via, f"{EQUIVALENTES.get(tipo, tipo)} {resto}"]
        opciones = [self.vertices[c] for c in dict.fromkeys(candidatas) if c in self.vertices]
        if not opciones:
            raise ValueError(f"'{nombre}': la via '{via}' no aparece en la Malla Vial")
        return opciones

    @staticmethod
    def _contacto(a: set, b: set) -> np.ndarray | None:
        """Vertices donde se tocan las dos vias, o None si no se cruzan."""
        comunes = a & b
        if comunes:
            return np.array(sorted(comunes))
        return MallaVial._puntos_mas_cercanos(a, b)

    @staticmethod
    def _centro(puntos: np.ndarray, nombre: str) -> tuple[float, float]:
        # Agrupa los puntos de contacto: un grupo es un cruce; varios grupos son cruces distintos
        grupos: list[list[np.ndarray]] = []
        for punto in puntos:
            cercano = next((g for g in grupos if any(np.abs(punto - q).max() * METROS_POR_GRADO < MISMO_CRUCE_M
                                                     for q in g)), None)
            if cercano is None:
                grupos.append([punto])
            else:
                cercano.append(punto)
        if len(grupos) > 1:
            raise ValueError(f"'{nombre}': las vias se cruzan en {len(grupos)} lugares; indica lat y lng a mano")
        lng, lat = np.mean(grupos[0], axis=0)
        return round(float(lat), 5), round(float(lng), 5)

    @staticmethod
    def _puntos_mas_cercanos(a: set, b: set) -> np.ndarray | None:
        """Vias que se cruzan sin compartir vertice: sus dos vertices mas cercanos, si estan cerca."""
        pa, pb = np.array(list(a)), np.array(list(b))
        mejor = (np.inf, None, None)
        for punto in pa:
            distancias = np.abs(pb - punto).max(axis=1)
            i = int(distancias.argmin())
            if distancias[i] < mejor[0]:
                mejor = (distancias[i], punto, pb[i])
        separacion, p1, p2 = mejor
        if separacion * METROS_POR_GRADO > MAX_SEPARACION_M:
            return None
        return np.array([p1, p2])
