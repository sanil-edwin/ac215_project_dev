#!/bin/bash

# AgriGuard MS4 Deployment Script
# Deploys both API and Frontend to Google Cloud Run

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  AgriGuard MS4 Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Configuration
PROJECT_ID="agriguard-ac215"
REGION="us-central1"
REGISTRY="us-central1-docker.pkg.dev"
REPO="agriguard"

API_IMAGE="${REGISTRY}/${PROJECT_ID}/${REPO}/api-ms4:latest"
FRONTEND_IMAGE="${REGISTRY}/${PROJECT_ID}/${REPO}/frontend-ms4:latest"

# Check if gcloud is configured
echo -e "\n${YELLOW}Checking GCP configuration...${NC}"
gcloud config set project ${PROJECT_ID}

# Step 1: Build and Push API
echo -e "\n${YELLOW}Step 1: Building API container...${NC}"
docker build -f Dockerfile.api -t ${API_IMAGE} .

echo -e "${YELLOW}Pushing API to Artifact Registry...${NC}"
docker push ${API_IMAGE}

echo -e "${GREEN}✓ API image pushed${NC}"

# Step 2: Deploy API to Cloud Run
echo -e "\n${YELLOW}Step 2: Deploying API to Cloud Run...${NC}"
gcloud run deploy agriguard-api-ms4 \
  --image=${API_IMAGE} \
  --platform=managed \
  --region=${REGION} \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300 \
  --max-instances=10 \
  --service-account=agriguard-service-account@${PROJECT_ID}.iam.gserviceaccount.com

# Get API URL
API_URL=$(gcloud run services describe agriguard-api-ms4 --region=${REGION} --format='value(status.url)')
echo -e "${GREEN}✓ API deployed at: ${API_URL}${NC}"

# Step 3: Build Frontend with API URL
echo -e "\n${YELLOW}Step 3: Building Frontend container...${NC}"
docker build \
  -f Dockerfile.frontend \
  --build-arg NEXT_PUBLIC_API_URL=${API_URL} \
  -t ${FRONTEND_IMAGE} .

echo -e "${YELLOW}Pushing Frontend to Artifact Registry...${NC}"
docker push ${FRONTEND_IMAGE}

echo -e "${GREEN}✓ Frontend image pushed${NC}"

# Step 4: Deploy Frontend to Cloud Run
echo -e "\n${YELLOW}Step 4: Deploying Frontend to Cloud Run...${NC}"
gcloud run deploy agriguard-frontend-ms4 \
  --image=${FRONTEND_IMAGE} \
  --platform=managed \
  --region=${REGION} \
  --allow-unauthenticated \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --max-instances=10 \
  --set-env-vars=NEXT_PUBLIC_API_URL=${API_URL}

# Get Frontend URL
FRONTEND_URL=$(gcloud run services describe agriguard-frontend-ms4 --region=${REGION} --format='value(status.url)')

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete! 🎉${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${GREEN}API URL:${NC}"
echo -e "  ${API_URL}"
echo -e "\n${GREEN}Frontend URL:${NC}"
echo -e "  ${FRONTEND_URL}"
echo -e "\n${GREEN}Health Check:${NC}"
echo -e "  curl ${API_URL}/health"
echo -e "\n${GREEN}Test API:${NC}"
echo -e "  curl ${API_URL}/api/counties"
echo -e "\n${YELLOW}Open your browser to:${NC}"
echo -e "  ${FRONTEND_URL}"
echo -e "\n${GREEN}========================================${NC}"

# Save URLs to file
echo "API_URL=${API_URL}" > deployment_urls.txt
echo "FRONTEND_URL=${FRONTEND_URL}" >> deployment_urls.txt

echo -e "${GREEN}URLs saved to deployment_urls.txt${NC}"
