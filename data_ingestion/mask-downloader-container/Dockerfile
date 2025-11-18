# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for geospatial libraries
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mask_downloader.py .
COPY utils/ ./utils/

# Create temp directory for downloads
RUN mkdir -p /app/temp

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TEMP_DIR=/app/temp
ENV START_YEAR=2010

# Run the mask downloader
CMD ["python", "mask_downloader.py"]
