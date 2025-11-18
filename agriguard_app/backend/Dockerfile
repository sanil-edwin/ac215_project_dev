# Backend Dockerfile for FastAPI app (backend/main.py)

# 1) Base image
FROM python:3.11-slim

# 2) Basic Python settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 3) System deps + uv (matches your other containers)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir uv

# 4) Workdir inside the container
WORKDIR /app

# 5) Install Python deps
# Expecting backend/requirements.txt in the repo at build time
COPY backend/requirements.txt /deps/backend.txt
RUN uv pip install --system -r /deps/backend.txt

# 6) Copy backend source code
# Keep "backend" as a package so we can use `backend.main:app`
COPY backend /app/backend

# 7) Port config
# - Locally: defaults to 8000
# - On Cloud Run: Cloud Run will inject $PORT
ENV PORT=8000

# 8) Start FastAPI with Uvicorn
# IMPORTANT: FastAPI instance must be `app` in backend/main.py
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
