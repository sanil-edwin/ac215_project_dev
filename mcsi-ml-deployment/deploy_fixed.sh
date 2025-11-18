#!/bin/bash

set -e

PROJECT_ID="agriguard-ac215"
REGION="us-central1"
REGISTRY="us-central1-docker.pkg.dev"
REPO="agriguard"

echo "[INFO] Building and pushing containers to Artifact Registry..."

# MCSI Processor
echo "[INFO] Building MCSI container..."
cd containers/mcsi_processing
docker build -t ${REGISTRY}/${PROJECT_ID}/${REPO}/mcsi-processor:latest .
docker push ${REGISTRY}/${PROJECT_ID}/${REPO}/mcsi-processor:latest
cd ../..

# Model Training
echo "[INFO] Building training container..."
cd containers/model_training
docker build -t ${REGISTRY}/${PROJECT_ID}/${REPO}/model-training:latest .
docker push ${REGISTRY}/${PROJECT_ID}/${REPO}/model-training:latest
cd ../..

# Model Serving
echo "[INFO] Building serving container..."
cd containers/model_serving
docker build -t ${REGISTRY}/${PROJECT_ID}/${REPO}/model-serving:latest .
docker push ${REGISTRY}/${PROJECT_ID}/${REPO}/model-serving:latest
cd ../..

echo "[INFO] All containers built and pushed successfully!"
echo "[INFO] Deploying to Cloud Run..."

# Deploy MCSI API
gcloud run deploy mcsi-api \
    --image ${REGISTRY}/${PROJECT_ID}/${REPO}/mcsi-processor:latest \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2

# Deploy Serving API
gcloud run deploy yield-prediction-api \
    --image ${REGISTRY}/${PROJECT_ID}/${REPO}/model-serving:latest \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2

echo "[INFO] Deployment complete!"
