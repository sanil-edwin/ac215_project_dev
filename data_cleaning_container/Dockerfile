# data-cleaning-container/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy cleaning code
COPY src/ ./src/

# Entry point
CMD ["python", "src/clean_data.py"]