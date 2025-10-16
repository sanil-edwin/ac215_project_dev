FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

WORKDIR /app

# Requirements per stage
COPY ML/data-ingestion/requirements.txt /deps/ingest.txt
COPY ML/data-preprocessing/requirements.txt /deps/pre.txt
COPY ML/model-yield-forecasting/requirements.txt /deps/yield.txt

RUN uv pip install --system -r /deps/ingest.txt
RUN uv pip install --system -r /deps/pre.txt
RUN uv pip install --system -r /deps/yield.txt

# Source per stage
COPY ML/data-ingestion/src /app/data-ingestion/src
COPY ML/data-ingestion/configs /app/data-ingestion/configs
COPY ML/data-preprocessing/src /app/data-preprocessing/src
COPY ML/data-preprocessing/configs /app/data-preprocessing/configs
COPY ML/model-yield-forecasting/src /app/model-yield-forecasting/src
COPY ML/model-yield-forecasting/configs /app/model-yield-forecasting/configs

# Orchestrator
COPY ML/workflow/run_workflow.py /app/run_workflow.py

ENV PYTHONPATH="/app/data-ingestion/src:/app/data-preprocessing/src:/app/model-yield-forecasting/src:${PYTHONPATH}"
CMD ["python", "run_workflow.py"]
