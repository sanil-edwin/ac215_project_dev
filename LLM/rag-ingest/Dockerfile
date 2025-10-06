FROM python:3.12-slim-bookworm


# install deps first for fast rebuilds (uses lock if present)
ENV UV_PROJECT_ENVIRONMENT=/home/app/.venv
ENV HF_HOME=/home/app/.cache/huggingface

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libxml2 libxslt1.1 ffmpeg ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN pip install -U pip uv
WORKDIR /app

COPY pyproject.toml README.md uv.lock* ./
ARG EXTRAS=""
RUN if [ -f uv.lock ]; then \
      if [ -n "$EXTRAS" ]; then uv sync --frozen --extra "$EXTRAS"; else uv sync --frozen; fi; \
    else \
      if [ -n "$EXTRAS" ]; then uv sync --extra "$EXTRAS"; else uv sync; fi; \
    fi

# bring in code
COPY ./ /apps

# DEV: start a bash shell and activate the uv-created venv
ENTRYPOINT ["/bin/bash","-lc"]
CMD ["source /home/app/.venv/bin/activate && exec bash"]