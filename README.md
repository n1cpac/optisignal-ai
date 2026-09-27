# OptiSignal-AI

Sistema de visión por computador para la detección y verificación óptica autónoma de fallas en semáforos viales mediante inspección externa.

Proyecto de curso — Visión por Computador  
Universidad Militar Nueva Granada (UMNG)

**Autores:** Juan Cerón, Juan Camilo Niño, Nicolás Acevedo

> **Estado del proyecto:** En fase de desarrollo y estructuración técnica.

> **Documentación del pipeline:** Los archivos `.md` principales forman parte del pipeline. Antes de realizar cambios importantes, consulta la documentación correspondiente. Después de modificar el pipeline, la estructura de datos, los datasets o cualquier proceso importante, actualiza la documentación para reflejar el estado real del proyecto.

---

## Descripción

OptiSignal-AI propone verificar si un semáforo está funcionando correctamente a partir únicamente de lo que una cámara observa, sin depender ni conectarse a ningún controlador de tráfico externo. 

Los sistemas tradicionales detectan fallas evaluando parámetros eléctricos internos (como el consumo de corriente en módulos LED), lo cual presenta una limitación crítica: no constatan si la señal es efectivamente visible hacia la vía (lentes obstruidos, suciedad acumulada, roturas o degradación del policarbonato). OptiSignal-AI audita el funcionamiento desde la perspectiva óptica directa mediante una filosofía de supervisión no invasiva tipo "caja negra".

---

## Enfoque técnico

El pipeline de procesamiento opera de forma secuencial y desacoplada:

1. **Detección del cabezal:** Un modelo de aprendizaje profundo de una sola etapa (YOLO) localiza espacialmente la estructura del semáforo en el fotograma.
2. **Aislamiento y clasificación cromática:** La región delimitada se divide verticalmente en tres subregiones (lentes rojo, amarillo y verde). Mediante procesamiento digital en espacio de color HSV con OpenCV, se evalúa la saturación y el brillo para determinar qué luz se encuentra encendida o si los lentes están apagados.
3. **Validación temporal autónoma (FSM):** El estado visual observado se procesa mediante una Máquina de Estados Finitos (FSM) que valida la coherencia secuencial. Esta máquina está adaptada a la normativa vial colombiana, donde las transiciones entre fases restrictivas y permisivas deben pasar obligatoriamente por luz amarilla:
   $$\text{ROJO} \longrightarrow \text{AMARILLO}_{\text{prep}} \longrightarrow \text{VERDE} \longrightarrow \text{AMARILLO}_{\text{desp}} \longrightarrow \text{ROJO}$$
   Discrepancias sostenidas (dos luces encendidas al tiempo, apagado total, omisión del amarillo o estados trabados más allá de su temporización) disparan alertas automáticas.

El desacoplamiento entre el detector visual y la máquina de estados permite entrenar la red sobre datos visuales genéricos y ajustar de forma modular la lógica de secuencia a cualquier regulación vial local.

---

## Datasets de referencia

El entrenamiento y la evaluación se fundamentan exclusivamente en dos repositorios de referencia, que se mantienen independientes:

- **[LISA Traffic Light Dataset](https://cvrr.ucsd.edu/):** secuencias diurnas/nocturnas con CSV de anotaciones.
- **Bosch Small Traffic Lights Dataset (BSTLD):** imágenes con cajas en anotaciones YAML.

El pipeline prioriza `data/datasets/lisa` y `data/datasets/bosch` locales. Si falta alguno, `data/scripts/prepare_datasets.py` usa como fallback la carpeta compartida de [Google Drive](https://drive.google.com/drive/folders/1_Q2jS-ZgivHq8bc2KpVxw58tIeP60f5x?usp=sharing), después convierte, particiona y valida ambos datasets. La estructura original de cada fuente se conserva en `data/datasets/`; los derivados quedan en `data/processed/{lisa,bosch}/` sin fusionar fuentes ni modificar la raw data. Consulta [PHASE_3_DATASETS_GUIDE.md](PHASE_3_DATASETS_GUIDE.md) para instalación y comandos.

---

## Interfaz de gestión

Como componente de visualización y monitoreo, el sistema integra una interfaz web construida en Angular y un backend en FastAPI con base de datos SQLite. Esta plataforma permite centralizar y registrar las alertas generadas por el pipeline de visión, visualizando el estado actual y el historial de anomalías.

---

## Validación experimental

Para la validación del sistema en laboratorio se contempla un semáforo a escala controlada basado en un microcontrolador ESP32 con diodos LED (rojo, amarillo y verde) y una cámara fija con línea de vista directa. El prototipo permite simular de forma controlada el ciclo normal de conmutación e inyectar fallas inducidas (luces simultáneas, apagón total o secuencias incorrectas) para corroborar la precisión del sistema de visión.
