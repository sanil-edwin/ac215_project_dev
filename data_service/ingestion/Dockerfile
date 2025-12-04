# Multi-stage Python image for AgriGuard data ingestion
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install all system dependencies upfront
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV PYTHONUNBUFFERED=1

# Create temp directory for downloads
RUN mkdir -p /app/temp /app/logs

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY downloaders/ ./downloaders/
COPY utils/ ./utils/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Entry point - expects DOWNLOAD_TYPE environment variable
# Or use: docker run ... python main.py --download mask
CMD ["python", "main.py", "--download", "mask"]
