FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y docker.io docker-compose-plugin && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
COPY requirements.txt ./requirements.txt
RUN uv pip install --system -r requirements.txt
COPY run_workflow.py ./run_workflow.py
CMD ["python","run_workflow.py","--start-year","2015","--end-year","2024","--sample"]
