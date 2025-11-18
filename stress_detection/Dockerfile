# =====================================================
#  AgriGuard – Iowa Corn Stress Detection & RAG Service
#  Builds a single container that can:
#   • Train the CSI calibrator  (python -m agriguard.models.train_calibrator)
#   • Serve FastAPI endpoints   (/stress, /stress/prob, /model/metrics, /rag/*)
# =====================================================

FROM python:3.11-slim AS base

# ---- System setup ----
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ---- App directory ----
WORKDIR /app

# ---- Copy requirements and install ----
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt

# ---- Prefetch NLTK data (used by RAG for sentence splitting) ----
RUN python -m nltk.downloader punkt --quiet || true

# ---- Copy source ----
COPY agriguard /app/agriguard
COPY tests /app/tests
COPY Makefile /app/Makefile

# ---- Ensure runtime directories exist ----
RUN mkdir -p /app/rag_store /artifacts

# ---- Default environment variables ----
ENV AG_BUCKET_ROOT="gs://agriguard-ac215-data" \
    AG_DATA_PREFIX="data_raw" \
    AG_MODEL_PATH="/artifacts/csi_calibrator.joblib" \
    RAG_DB_PATH="/app/rag_store" \
    PYTHONPATH="/app"

# ---- Expose FastAPI port ----
EXPOSE 8000

# ---- Command ----
# Default: run FastAPI app with uvicorn
# You can override entrypoint to run training instead.
CMD ["uvicorn", "agriguard.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

