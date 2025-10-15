#!/bin/bash

# AgriGuard Preprocessing Container - Interactive Shell
# Provides easy access to container for development and debugging

set -e

# Configuration
IMAGE_NAME="agriguard-preprocessing"
CONTAINER_NAME="agriguard-preprocessing-shell"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if secrets directory exists
if [ ! -d "secrets" ]; then
    echo -e "${RED}Error: secrets/ directory not found${NC}"
    echo "Please create secrets/ directory with gcp-key.json"
    exit 1
fi

# Check if GCP key exists
if [ ! -f "secrets/gcp-key.json" ]; then
    echo -e "${RED}Error: secrets/gcp-key.json not found${NC}"
    echo "Please add your GCP service account key to secrets/gcp-key.json"
    exit 1
fi

# Build image if it doesn't exist
if [[ "$(docker images -q ${IMAGE_NAME} 2> /dev/null)" == "" ]]; then
    echo -e "${YELLOW}Image not found. Building ${IMAGE_NAME}...${NC}"
    docker build -t ${IMAGE_NAME} .
fi

# Environment variables
export GCS_BUCKET_NAME=${GCS_BUCKET_NAME:-"agriguard-ac215-data"}
export GCP_PROJECT_ID=${GCP_PROJECT_ID:-"agriguard-ac215"}
export YEAR=${YEAR:-"2025"}

echo -e "${GREEN}Starting interactive shell for ${IMAGE_NAME}${NC}"
echo "Environment:"
echo "  - GCS_BUCKET_NAME: ${GCS_BUCKET_NAME}"
echo "  - GCP_PROJECT_ID: ${GCP_PROJECT_ID}"
echo "  - YEAR: ${YEAR}"
echo ""

# Run container with interactive shell
docker run --rm -it \
    --name ${CONTAINER_NAME} \
    -v "$(pwd)/secrets:/secrets:ro" \
    -v "$(pwd)/src:/app/src" \
    -v "$(pwd)/config:/app/config" \
    -v "$(pwd)/logs:/app/logs" \
    -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json \
    -e GCS_BUCKET_NAME=${GCS_BUCKET_NAME} \
    -e GCP_PROJECT_ID=${GCP_PROJECT_ID} \
    -e YEAR=${YEAR} \
    ${IMAGE_NAME} \
    /bin/bash

echo -e "${GREEN}Shell session ended${NC}"
