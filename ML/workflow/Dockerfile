FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Base build tools + uv
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy entire service directories so COPY never fails on missing subfolders
# (robust for CI and current repo layout)
COPY ML/data-ingestion/ /app/data-ingestion/
COPY ML/preprocessing/ /app/preprocessing/
COPY ML/model-yield-forecasting/ /app/model-yield-forecasting/

# Orchestrator
COPY ML/workflow/run_workflow.py /app/run_workflow.py

# Install dependencies per component:
# - If requirements.txt exists, use it
# - else if pyproject.toml exists, install editable (-e)
RUN if [ -f /app/data-ingestion/requirements.txt ]; then \
      uv pip install --system -r /app/data-ingestion/requirements.txt; \
    elif [ -f /app/data-ingestion/pyproject.toml ]; then \
      uv pip install --system -e /app/data-ingestion; \
    fi

RUN if [ -f /app/preprocessing/requirements.txt ]; then \
      uv pip install --system -r /app/preprocessing/requirements.txt; \
    elif [ -f /app/preprocessing/pyproject.toml ]; then \
      uv pip install --system -e /app/preprocessing; \
    fi

RUN if [ -f /app/model-yield-forecasting/requirements.txt ]; then \
      uv pip install --system -r /app/model-yield-forecasting/requirements.txt; \
    elif [ -f /app/model-yield-forecasting/pyproject.toml ]; then \
      uv pip install --system -e /app/model-yield-forecasting; \
    fi

# Python path to import the modules
ENV PYTHONPATH="/app/data-ingestion/src:/app/preprocessing/src:/app/model-yield-forecasting/src:${PYTHONPATH}"
CMD ["python", "run_workflow.py"]
