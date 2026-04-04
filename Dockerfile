FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NEXT_TELEMETRY_DISABLED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    build-essential \
    libpq-dev \
    curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./frontend/
WORKDIR /app/frontend
RUN npm ci

WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r /app/backend/requirements.txt

COPY frontend /app/frontend
COPY backend /app/backend
COPY render-start.sh /app/render-start.sh

WORKDIR /app/frontend
ARG NEXT_PUBLIC_API_URL=/api
ARG INTERNAL_API_URL=http://127.0.0.1:8000/api
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    INTERNAL_API_URL=$INTERNAL_API_URL
RUN npm run build

RUN chmod +x /app/render-start.sh && mkdir -p /app/data

EXPOSE 10000

CMD ["/app/render-start.sh"]
