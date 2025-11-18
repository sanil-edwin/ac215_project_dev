# Dockerfile for Model Training Container
# Used for training LightGBM + Random Forest ensemble

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create models directory
RUN mkdir -p /app/models

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "src/train_model.py"]
