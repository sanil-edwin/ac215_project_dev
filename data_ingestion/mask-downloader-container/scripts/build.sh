#!/bin/bash

# Build Docker image for mask downloader
# This script builds and optionally pushes to Google Container Registry

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-agriguard-ac215}"
IMAGE_NAME="mask-downloader"
VERSION="${VERSION:-latest}"
REGION="${REGION:-us-central1}"

# Full image name
FULL_IMAGE_NAME="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${VERSION}"

echo "======================================"
echo "Building Mask Downloader Container"
echo "======================================"
echo "Project ID: ${PROJECT_ID}"
echo "Image: ${FULL_IMAGE_NAME}"
echo "======================================"

# Build the Docker image
echo "Building Docker image..."
docker build -t ${IMAGE_NAME}:${VERSION} .
docker tag ${IMAGE_NAME}:${VERSION} ${FULL_IMAGE_NAME}

echo "✓ Build complete: ${FULL_IMAGE_NAME}"

# Ask if user wants to push to GCR
read -p "Push to Google Container Registry? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Pushing to GCR..."
    docker push ${FULL_IMAGE_NAME}
    echo "✓ Image pushed to GCR"
    
    echo ""
    echo "======================================"
    echo "Next Steps:"
    echo "======================================"
    echo "1. Deploy to Cloud Run:"
    echo "   ./scripts/deploy-cloudrun.sh"
    echo ""
    echo "2. Or run manually:"
    echo "   gcloud run jobs create mask-downloader \\"
    echo "     --image ${FULL_IMAGE_NAME} \\"
    echo "     --region ${REGION} \\"
    echo "     --service-account mask-downloader@${PROJECT_ID}.iam.gserviceaccount.com"
fi

echo ""
echo "✓ Build script complete"
