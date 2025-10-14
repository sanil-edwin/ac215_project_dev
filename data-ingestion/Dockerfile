FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for geospatial processing
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    libhdf4-alt-dev \
    libnetcdf-dev \
    curl \
    wget \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Copy dependency file
COPY pyproject.toml .

# Install Python dependencies using uv
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -e .

RUN pip install --no-cache-dir pyhdf earthengine-api pyarrow

# Install pyhdf for MODIS HDF file processing
RUN pip install --no-cache-dir pyhdf

RUN pip install --no-cache-dir earthengine-api

# Copy source code
COPY src/ ./src/
COPY config/ ./config/

# Create necessary directories
RUN mkdir -p /temp /logs

# Set Google Cloud credentials path
ENV GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json

# Default command
CMD ["python", "src/data_ingestion/modis_downloader.py"]
