# Raw datasets

Coloca aquí las estructuras originales de cada fuente, sin renombrar ni modificar sus archivos:

- `lisa/`: secuencias y CSV nativos de LISA.
- `bosch/`: BSTLD, imágenes `rgb/` y su YAML de anotaciones.

El resolvedor local-first detecta ambas carpetas. Si falta alguna, intenta obtener la carpeta compartida configurada en `data/scripts/download_datasets.py`. Los datos quedan excluidos de Git por este directorio.
