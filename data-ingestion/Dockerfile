FROM python:3.11-slim

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY configs/ ./configs/

# Create directories
RUN mkdir -p /app/data /app/secrets /app/logs

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Metadata
LABEL maintainer="AgriGuard Team"
LABEL version="1.0.0"
LABEL description="Data Ingestion for Iowa corn monitoring"

# Default command
CMD ["python", "src/download_yield_data.py", "--help"]
