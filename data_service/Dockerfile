FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (in same folder as Dockerfile)
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy validation and processing modules (relative to data/)
COPY validation/ validation/
COPY processing/ processing/

# Copy complete pipeline script (in same folder as Dockerfile)
COPY pipeline_complete.py .

# Run complete pipeline (Ingestion → Processing → Validation)
CMD ["python", "pipeline_complete.py"]
