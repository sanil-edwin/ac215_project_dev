# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY yield_downloader.py .
COPY utils/ ./utils/

# Create temp directory
RUN mkdir -p /app/temp

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TEMP_DIR=/app/temp

# Run the yield downloader
CMD ["python", "yield_downloader.py"]
