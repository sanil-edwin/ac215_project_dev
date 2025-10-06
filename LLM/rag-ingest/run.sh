#!/usr/bin/env bash
set -e

IMG=agriguard-ingest:dev
SA="/Users/binhvu/Desktop/cs215/gcp_keys/agriguard-ac215-1de1b7432036.json"

docker run --rm -it \
  --tmpfs /tmp \
  -v "$PWD:/app:ro" \
  -v "$SA:/run/secrets/gcp.json:ro" \
  -e GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp.json \
  -e GCS_BUCKET=agriguard-ac215-data \
  -e GCS_BASE_PREFIX=RAG_pipeline \
  -e DATA_DIR=/tmp/data \
  -e INDEX_DIR=/tmp/indexes \
  "$IMG"