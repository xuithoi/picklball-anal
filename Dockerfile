# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi; \
    npm ci --strict-ssl=true
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl ffmpeg libglib2.0-0 libgl1 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY backend/requirements.txt ./requirements.txt
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca CURL_CA_BUNDLE=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir 'torch==2.7.0+cpu' 'torchvision==0.22.0+cpu' --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /srv/models \
    && curl --fail --location --retry 2 https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt -o /srv/models/yolo11n.pt
COPY backend/app ./app
COPY --from=frontend /web/dist ./frontend/dist
ENV FRONTEND_DIST=/srv/frontend/dist \
    DATA_DIR=/var/data/jobs \
    YOLO_MODEL=/srv/models/yolo11n.pt \
    YOLO_CONFIG_DIR=/tmp/kun-ai/ultralytics \
    MPLCONFIGDIR=/tmp/kun-ai/matplotlib \
    XDG_CACHE_HOME=/tmp/kun-ai/cache \
    OMP_NUM_THREADS=2 \
    PYTHONUNBUFFERED=1
EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '10000') + '/api/health', timeout=4)"
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-10000}\" --workers 1"]
