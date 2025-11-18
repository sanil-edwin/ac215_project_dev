# Backend Dockerfile for FastAPI app (backend/main.py)

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir uv

WORKDIR /app

# Expecting backend/requirements.txt in the repo at build time
COPY backend/requirements.txt /deps/backend.txt
RUN uv pip install --system -r /deps/backend.txt

# Keep "backend" as a package so we can use `backend.main:app`
COPY backend /app/backend

# - Locally: defaults to 8000
# - On Cloud Run: Cloud Run will inject $PORT
ENV PORT=8000

# Start FastAPI with Uvicorn
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
