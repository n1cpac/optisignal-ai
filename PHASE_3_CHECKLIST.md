# Checklist de Fase 3 — Datasets

## Implementado

- [x] Limitar las fuentes a LISA y Bosch (BSTLD).
- [x] Detectar estructura nativa local y evitar descargas cuando los datos existen.
- [x] Descargar desde Google Drive como fallback para fuentes ausentes.
- [x] Convertir anotaciones LISA CSV y Bosch YAML a una clase YOLO.
- [x] Mantener los proveedores independientes y su raw data intacta.
- [x] Crear particiones reproducibles 70/20/10, manifiestos y `data.yaml`.
- [x] Validar etiquetas e imágenes.
- [x] Ignorar raw data y derivados pesados mediante reglas Git.
- [x] Sincronizar README, guía, reporte y plan con el pipeline.
- [x] Ejecutar conversión, partición y validación local de ambos datasets (`PASS`).

## Validación operacional

La ejecución local produjo 36,775 imágenes LISA y 7,147 Bosch, ambas con 0 etiquetas ausentes o inválidas. No se versionan los resultados que contienen datos derivados pesados.

**Estado de implementación:** Fase 3 implementada y validada con los datasets locales disponibles.
