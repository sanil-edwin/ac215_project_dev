# Preprocessing Container - AgriGuard
# Computes baselines, anomalies, and ML features from MODIS data

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files first
COPY pyproject.toml ./
COPY README.md ./
COPY src/ ./src/
COPY config/ ./config/

# Install dependencies with pip (simpler than uv)
RUN pip install --no-cache-dir -e .

# Create necessary directories
RUN mkdir -p /temp /logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
ENV TEMP_DIR=/temp
ENV PYTHONPATH=/app/src

# Default command
CMD ["python", "src/preprocessing/run_preprocessing.py"]