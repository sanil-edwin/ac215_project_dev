# Dockerfile for MCSI Processing Container
# Used for weekly MCSI calculations and Cloud Run Jobs

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Set Python path
ENV PYTHONPATH=/app

# Default command (can be overridden)
CMD ["python", "src/mcsi_calculator.py"]
