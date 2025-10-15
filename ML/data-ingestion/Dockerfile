FROM python:3.11-slim-bookworm

# Safer defaults for CI builds
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies for geospatial processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    libhdf4-alt-dev \
    libnetcdf-dev \
    curl \
    wget \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# GDAL environment variables
ENV GDAL_CONFIG=/usr/bin/gdal-config \
    CPLUS_INCLUDE_PATH=/usr/include/gdal \
    C_INCLUDE_PATH=/usr/include/gdal

# Dependency metadata
COPY pyproject.toml .

# Use uv for Python deps
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -e .

# Extra libs needed at runtime
RUN pip install --no-cache-dir pyhdf earthengine-api pyarrow

# App code and config
COPY src/ ./src/
COPY config/ ./config/

# Required dirs
RUN mkdir -p /temp /logs

# GCP creds path
ENV GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json

# Default command
CMD ["python", "src/data_ingestion/modis_downloader.py"]
