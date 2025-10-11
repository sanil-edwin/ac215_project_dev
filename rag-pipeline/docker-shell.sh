#!/bin/bash

# exit immediately if a command exits with a non-zero status
set -e

# Set variables
export BASE_DIR=$(pwd)
export SECRETS_DIR=$(pwd)/../../secrets/
export GCP_PROJECT="agriguard-ac215"
export GCP_LOCATION="us-central1"
export GCS_BUCKET="agriguard-ac215-data"

# Model configuration (can override defaults in compose)
export EMBEDDING_MODEL="text-embedding-004" 
export EMBEDDING_DIMENSION="768"
export GENERATIVE_MODEL="gemini-2.0-flash-001"

# mount current creds into this docker container path
export GOOGLE_APPLICATION_CREDENTIALS="/secrets/agriguard-service-account.json"
export IMAGE_NAME="agri-rag-cli"

# Create the network if we don't have it yet
docker network inspect agri-rag-network >/dev/null 2>&1 || docker network create agri-rag-network

# Build the image based on the Dockerfile
docker build -t $IMAGE_NAME -f Dockerfile .

# Run All Containers
docker-compose run --rm --service-ports $IMAGE_NAME
