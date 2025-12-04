#!/bin/bash

# exit immediately if a command exits with a non-zero status
set -e

# Define some environment variables
export IMAGE_NAME="agriguard-api-service"
export BASE_DIR=$(pwd)
# Secrets are at the same level as ac215_project_dev (go up 3 levels from src/api_service/)
export SECRETS_DIR=$(cd ../../.. && pwd)/secrets/
export PERSISTENT_DIR=$(pwd)/

# Build the image based on the Dockerfile
#docker build -t $IMAGE_NAME -f Dockerfile .
# M1/2 chip macs use this line
docker build -t $IMAGE_NAME --platform=linux/arm64/v8 -f Dockerfile .

# Run the container
docker run --rm --name $IMAGE_NAME -ti \
-v "$BASE_DIR":/app \
-v "$SECRETS_DIR":/secrets \
-v "$PERSISTENT_DIR":/persistent \
-p 8002:8002 \
-e DEV=0 \
-e MCSI_URL=http://mcsi:8000 \
-e MCSI_URL_LOCAL=http://localhost:8000 \
-e YIELD_URL=http://yield:8001 \
-e YIELD_URL_LOCAL=http://localhost:8001 \
-e RAG_URL=http://rag:8003 \
-e RAG_URL_LOCAL=http://localhost:8003 \
-e CHAT_HISTORY_DIR=/persistent/chat-history \
$IMAGE_NAME

