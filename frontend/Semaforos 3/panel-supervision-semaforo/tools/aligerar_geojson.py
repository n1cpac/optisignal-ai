"""
Aligera el GeoJSON de la Malla Vial Integral de Bogota para usarlo en el navegador.

- Descarta todos los atributos: el mapa dibuja todas las vias del mismo color y no usa ninguno.
- Redondea las coordenadas (5 decimales, aprox. 1 metro).
- Descarta tramos sin geometria y escribe el JSON compacto.

Uso:
    python tools/aligerar_geojson.py entrada.geojson src/assets/malla-vial-bogota.geojson
"""
import json
import sys

DECIMALES = 5


def redondear(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], DECIMALES), round(coords[1], DECIMALES)]
    return [redondear(c) for c in coords]


def main(entrada, salida):
    with open(entrada, encoding="utf-8") as f:
        datos = json.load(f)

    features = []
    for feat in datos["features"]:
        geom = feat.get("geometry")
        if not geom:
            continue
        features.append({
            "type": "Feature",
            "properties": {},
            "geometry": {"type": geom["type"], "coordinates": redondear(geom["coordinates"])},
        })

    with open(salida, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f,
                  separators=(",", ":"), ensure_ascii=False)
    print(f"{len(features)} tramos escritos en {salida}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
