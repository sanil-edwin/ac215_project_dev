#!/bin/bash
# Deploy ETo & PR Incremental Update Jobs
set -e

PROJECT_ID="agriguard-ac215"
REGION="us-central1"
REPO="agriguard-containers"

echo "Building and deploying ETo & Precipitation incremental update jobs..."

# Build and push ETo
echo "→ Building ETo image..."
docker build -f Dockerfile.update_eto -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/agriguard-update-eto:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/agriguard-update-eto:latest

# Build and push PR + Water Deficit
echo "→ Building Precipitation + Water Deficit image..."
docker build -f Dockerfile.update_pr -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/agriguard-update-pr:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/agriguard-update-pr:latest

# Create ETo job
echo "→ Creating ETo update job..."
gcloud run jobs create agriguard-update-eto \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/agriguard-update-eto:latest \
  --region=${REGION} \
  --memory=4Gi \
  --cpu=2 \
  --task-timeout=1h \
  --max-retries=2 \
  || echo "Job exists, updating..."

gcloud run jobs update agriguard-update-eto \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/agriguard-update-eto:latest \
  --region=${REGION} 2>/dev/null || true

# Create PR + Water Deficit job
echo "→ Creating Precipitation + Water Deficit update job..."
gcloud run jobs create agriguard-update-pr \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/agriguard-update-pr:latest \
  --region=${REGION} \
  --memory=4Gi \
  --cpu=2 \
  --task-timeout=1h \
  --max-retries=2 \
  || echo "Job exists, updating..."

gcloud run jobs update agriguard-update-pr \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/agriguard-update-pr:latest \
  --region=${REGION} 2>/dev/null || true

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Jobs created:"
echo "  • agriguard-update-eto - Updates ETo data"
echo "  • agriguard-update-pr  - Updates Precipitation + calculates Water Deficit"
echo ""
echo "Test jobs:"
echo "  gcloud run jobs execute agriguard-update-eto --region=${REGION}"
echo "  gcloud run jobs execute agriguard-update-pr --region=${REGION}"
