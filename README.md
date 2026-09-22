# OptiSignal-AI

Sistema de visión por computador para la detección y verificación óptica autónoma de fallas en semáforos viales.

Proyecto de curso — Visión por Computador
Universidad Militar Nueva Granada (UMNG)

**Autores:** Juan Ceron, Juan Camilo Niño, Nicolás Acevedo

> **Estado del proyecto:** en fase de planeación. Este repositorio contiene la propuesta y el diseño técnico; aún no se ha desarrollado ni implementado.

## Descripción

OptiSignal-AI propone verificar si un semáforo está funcionando correctamente a partir únicamente de lo que una cámara observa, sin depender de ningún controlador de tráfico externo. Los sistemas actuales detectan fallas midiendo la corriente eléctrica de cada módulo LED, lo cual no permite constatar si la señal es realmente visible (lente obstruido, sucio o degradado). OptiSignal-AI busca verificar la señal desde la perspectiva óptica directa.

## Enfoque técnico

1. **Detección:** un modelo de detección de objetos (YOLO) localiza el semáforo y cada uno de sus lentes (rojo, amarillo, verde).
2. **Clasificación:** se determina el estado visual de cada lente (encendido, apagado, anómalo u obstruido).
3. **Validación autónoma:** el estado observado se contrasta contra la lógica conocida de un semáforo — un solo color encendido a la vez, transiciones en el orden correcto, duración de fase dentro de un rango razonable — sin requerir el estado reportado por ningún controlador externo. Discrepancias sostenidas (dos colores encendidos a la vez, un color trabado más allá de su tiempo típico, un lente sin emisión cuando debería estarlo) se registran como anomalía.

Esta validación por máquina de estados es lo que hace que el sistema sea autónomo: no depende de acceso a infraestructura de tráfico real, opera únicamente sobre la señal visual observada.

## Interfaz de gestión

Como componente adicional, se contempla una interfaz que centralice las alertas generadas por el sistema de visión, permitiendo visualizar y priorizar las fallas detectadas. Es un complemento de valor práctico, subordinado al componente de visión por computador, que sigue siendo el eje central de la propuesta.

## Datasets de referencia

- [LISA Traffic Light Dataset](https://cvrr.ucsd.edu/) — ~43,000 imágenes, ~113,000 semáforos anotados con estado.
- Bosch Small Traffic Lights Dataset (BSTLD) — ~13,400 imágenes anotadas.
- DriveU Traffic Light Dataset (DTLD) — ~230,000 semáforos anotados.

## Validación planeada

Prototipo a escala reducida: semáforo miniatura con LEDs controlados por microcontrolador (ESP32) y una cámara fija enfrente. Las fallas se simulan de forma controlada (apagando un color, atenuando brillo, obstruyendo un lente) para validar la detección del sistema de visión.