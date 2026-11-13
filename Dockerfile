# Etapa 1: Compilar el panel web Angular
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend

COPY ["frontend/Semaforos 3/panel-supervision-semaforo/package.json", "frontend/Semaforos 3/panel-supervision-semaforo/package-lock.json", "./"]
RUN npm ci

COPY ["frontend/Semaforos 3/panel-supervision-semaforo/", "./"]
RUN npm run build

# Etapa 2: Backend FastAPI + Visión por Computador (CPU) + estáticos del panel
FROM python:3.12-slim-bookworm
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r backend/requirements.txt

COPY CONFIG_PARAMETERS.yaml ./CONFIG_PARAMETERS.yaml
COPY backend/ ./backend/
COPY models/ ./models/
COPY data/test_videos/ ./data/test_videos/
COPY data/history_scenes/ ./data/history_scenes/
COPY ["frontend/Semaforos 3/panel-supervision-semaforo/src/assets/malla-vial-bogota.geojson", "./frontend/Semaforos 3/panel-supervision-semaforo/src/assets/malla-vial-bogota.geojson"]
COPY --from=frontend-builder /frontend/dist/optisignal-panel/browser ./frontend_dist

RUN mkdir -p /app/data/db

ENV PYTHONPATH=/app/backend \
    PYTHONUNBUFFERED=1 \
    OPTISIGNAL_FRONTEND_DIST=/app/frontend_dist \
    OPTISIGNAL_DB_PATH=/app/data/db/optisignal.db

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
