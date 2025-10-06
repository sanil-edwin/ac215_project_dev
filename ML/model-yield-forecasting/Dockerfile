FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY configs/ ./configs/

RUN mkdir -p /app/data /app/models /app/logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

LABEL maintainer="AgriGuard Team"
LABEL version="1.0.0"
LABEL description="Yield forecasting model - supervised learning"

CMD ["python", "src/train_model.py", "--help"]
