# Reporte de preparación de datos

## Estado observado en el repositorio

- **LISA:** raw data local presente bajo `data/datasets/lisa/`; contiene carpetas de secuencias y anotaciones CSV bajo `Annotations/Annotations/`.
- **Bosch (BSTLD):** raw data local presente bajo `data/datasets/bosch/`; contiene imágenes PNG bajo `rgb/test/`, anotaciones `test.yaml` y licencia.
- **LISA procesado:** 36,775 imágenes y 232,348 cajas. Partición: 25,742 train, 7,355 val y 3,678 test. Validación: `PASS`, 0 etiquetas ausentes y 0 inválidas.
- **Bosch procesado:** 7,147 imágenes y 13,486 cajas. Partición: 5,002 train, 1,429 val y 716 test. Validación: `PASS`, 0 etiquetas ausentes y 0 inválidas.

## Reproducir y registrar resultados

Resultados obtenidos el 2026-09-27 usando la raw data local presente. Los derivados están ignorados por Git porque se reconstruyen desde la raw data.

## Resultado

La arquitectura preserva los originales, evita una fusión entre proveedores y usa Google Drive únicamente como fallback cuando falta un dataset local. La conversión y validación local finalizaron correctamente para ambas fuentes.
