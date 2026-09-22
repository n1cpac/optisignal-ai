# Distribución de responsabilidades del equipo — OptiSignal-AI

## Introducción

Este documento define los roles, responsabilidades y áreas de trabajo para los tres integrantes del equipo de desarrollo de OptiSignal-AI.

---

## Integrante 1: Visión por Computador y Datasets

### Responsabilidades principales

1. **Curaduría y estructuración de datasets abiertos**
   - Descargar y organizar los datasets LISA, BSTLD y DTLD
   - Homogeneizar las etiquetas al formato estándar de YOLO (`.txt`)
   - Realizar partición estadística: 70% entrenamiento, 20% validación, 10% pruebas
   - Documentar el proceso de preparación de datos

2. **Entrenamiento y benchmarking del detector YOLO**
   - Seleccionar versión ligera (YOLOv8n / YOLOv11n)
   - Realizar transferencia de aprendizaje (*transfer learning*)
   - Evaluar métricas: Precision, Recall, mAP@50
   - Exportar pesos óptimos a `models/best.pt`
   - Documentar resultados de entrenamiento

3. **Segmentación geométrica y análisis cromático**
   - Implementar división de ROI en tres zonas verticales (Rojo, Amarillo, Verde)
   - Desarrollar algoritmo de clasificación en espacio HSV
   - Definir y ajustar rangos de color para cada lente
   - Implementar detección de brillo insuficiente y lentes obstruidos
   - Crear módulo `classifier.py` en el backend

4. **Pruebas y validación de visión**
   - Probar inferencia en tiempo real con OpenCV
   - Evaluar rendimiento en diferentes condiciones de iluminación
   - Generar matriz de confusión para clasificación cromática
   - Documentar casos de borde y limitaciones

### Archivos principales

```
backend/app/detector.py
backend/app/classifier.py
data/datasets/
models/best.pt
REPORTS/vision_performance.md
```

### Hitos de la Fase 1

- [ ] Datasets descargados y estructurados
- [ ] Formato YOLO homogeneizado
- [ ] Partición estadística completada
- [ ] Documentación de preparación de datos

---

## Integrante 2: Lógica de Control y Backend

### Responsabilidades principales

1. **Máquina de estados finitos (FSM)**
   - Implementar la secuencia colombiana: Rojo → Amarillo → Verde → Amarillo → Rojo
   - Definir tabla de transiciones válidas e inválidas
   - Implementar histéresis temporal (ventana de N fotogramas)
   - Crear módulo `state_machine.py`
   - Documentar lógica de validación

2. **API REST con FastAPI**
   - Implementar endpoints: `/health`, `/status`, `/alerts`, `/alerts/{id}`, `DELETE /alerts`
   - Definir esquemas JSON para respuestas
   - Implementar autenticación básica (si es requerida)
   - Documentar API con Swagger/OpenAPI
   - Crear módulo `main.py`

3. **Gestión de base de datos SQLite**
   - Diseñar esquema de tablas para anomalías
   - Implementar CRUD operations
   - Almacenar timestamp, tipo de anomalía, estado observado, confianza, ruta de evidencia
   - Crear módulo `database.py`
   - Implementar backup automático

4. **Integración del pipeline**
   - Conectar salida de YOLO con clasificador HSV
   - Alimentar máquina de estados en cada ciclo
   - Registrar anomalías confirmadas en base de datos
   - Implementar manejo de errores y recuperación

5. **Pruebas unitarias e integración**
   - Crear tests para FSM
   - Crear tests para API endpoints
   - Crear tests para operaciones de base de datos
   - Documentar cobertura de tests

### Archivos principales

```
backend/app/main.py
backend/app/state_machine.py
backend/app/database.py
backend/app/models.py
backend/tests/
REPORTS/backend_api_spec.md
```

### Hitos de la Fase 1

- [ ] Especificación de FSM completada
- [ ] Tabla de transiciones documentada
- [ ] Esquema de base de datos diseñado
- [ ] Endpoints de API especificados

---

## Integrante 3: Frontend, Integración y Hardware

### Responsabilidades principales

1. **Desarrollo de interfaz web con Angular**
   - Crear componente dashboard con indicador visual del semáforo
   - Crear módulo de alertas con tabla histórica y filtros
   - Crear módulo de estado del sistema (FPS, recursos, contador de alertas)
   - Implementar componente visual reutilizable `traffic-light`
   - Implementar componente reutilizable `alert-card`
   - Configurar enrutamiento en `app.routes.ts`

2. **Comunicación frontend-backend**
   - Crear servicio `api.service.ts` para peticiones HTTP
   - Implementar polling periódico (1-2 segundos) al endpoint `/status`
   - Manejar errores de conexión y reconexión
   - Implementar actualización en tiempo real del estado

3. **Integración del sistema completo**
   - Integrar frontend con API REST del backend
   - Realizar pruebas end-to-end
   - Validar flujo completo: captura → detección → FSM → almacenamiento → visualización
   - Documentar procedimiento de integración

4. **Firmware de prototipo ESP32**
   - Programar secuencia normal colombiana en microcontrolador
   - Implementar comandos vía puerto serial para inyectar fallas
   - Crear interfaz de control de LEDs (Rojo, Amarillo, Verde)
   - Documentar procedimiento de pruebas de laboratorio

5. **Configuración de Docker Compose**
   - Crear `docker-compose.yml` con servicios backend y frontend
   - Configurar volúmenes para modelos y datos
   - Definir variables de entorno
   - Documentar procedimiento de ejecución

6. **Documentación general**
   - Crear `README.md` con instrucciones de instalación
   - Documentar procedimiento de ejecución local y vía Docker
   - Crear guía de uso de la interfaz web
   - Documentar troubleshooting común

### Archivos principales

```
frontend/src/app/
frontend/Dockerfile
prototype/esp32/
docker-compose.yml
README.md
CONTRIBUTING.md
```

### Hitos de la Fase 1

- [ ] Estructura de componentes Angular diseñada
- [ ] Servicio de API especificado
- [ ] Dockerfile para frontend creado
- [ ] Estructura de Docker Compose definida

---

## Comunicación y coordinación

### Reuniones

- **Reunión de planificación:** Inicio de cada semana (lunes)
- **Reunión de sincronización:** Mitad de semana (miércoles)
- **Reunión de cierre:** Fin de semana (viernes)
- **Duración:** 30-45 minutos cada una

### Canales de comunicación

- **GitLab Issues:** Para tareas y seguimiento
- **GitLab Merge Requests:** Para revisión de código
- **Documentación:** En archivos `.md` del repositorio
- **Chat:** Para comunicación rápida (si es disponible)

### Convención de ramas Git

```
main                          # Código estable
develop                       # Integración de features
feature/vision-*              # Features de visión (Integrante 1)
feature/backend-*             # Features de backend (Integrante 2)
feature/frontend-*            # Features de frontend (Integrante 3)
bugfix/*                      # Correcciones de bugs
```

### Revisión de código

- Mínimo 1 revisor antes de merge a `develop`
- Mínimo 2 revisores antes de merge a `main`
- Todos los tests deben pasar
- Documentación debe estar actualizada

---

## Dependencias entre roles

### Integrante 1 → Integrante 2
- Proporciona: Modelo YOLO entrenado (`best.pt`), especificación de clasificador HSV
- Recibe: Feedback sobre rendimiento en tiempo real

### Integrante 2 → Integrante 3
- Proporciona: API REST especificada, esquema de respuestas JSON
- Recibe: Feedback sobre usabilidad de endpoints

### Integrante 3 → Integrante 1 y 2
- Proporciona: Prototipo ESP32 para pruebas, Docker Compose para ejecución
- Recibe: Componentes finalizados para integración

---

## Criterios de aceptación por rol

### Integrante 1
- [ ] Datasets estructurados y documentados
- [ ] Modelo YOLO con mAP@50 ≥ 90%
- [ ] Clasificador HSV con precisión ≥ 95%
- [ ] Tiempo de inferencia < 35 ms por fotograma
- [ ] Documentación técnica completa

### Integrante 2
- [ ] FSM implementada y validada
- [ ] API REST funcional con todos los endpoints
- [ ] Base de datos SQLite con almacenamiento de anomalías
- [ ] Tests unitarios con cobertura ≥ 80%
- [ ] Documentación de API (Swagger)

### Integrante 3
- [ ] Dashboard Angular funcional
- [ ] Módulo de alertas con filtros
- [ ] Comunicación frontend-backend en tiempo real
- [ ] Docker Compose ejecutable
- [ ] Documentación de usuario completa

---

## Escalabilidad futura

Si el equipo crece:

- **Integrante 4:** QA y pruebas automatizadas
- **Integrante 5:** DevOps y despliegue en producción
- **Integrante 6:** Documentación técnica y capacitación
