FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN pip install --no-cache-dir uv
COPY requirements.txt ./requirements.txt
RUN uv pip install --system -r requirements.txt
COPY run_workflow.py ./run_workflow.py
CMD ["python","run_workflow.py","--start-year","2020","--end-year","2024","--sample"]
