#!/bin/bash

PROJECT_ID="agriguard-ac215"
REGION="us-central1"
SERVICE_ACCOUNT="agriguard-service-account@${PROJECT_ID}.iam.gserviceaccount.com"

echo "======================================================================"
echo "DEPLOYING INCREMENTAL UPDATE JOBS FOR ETo, PRECIPITATION & WATER DEFICIT"
echo "======================================================================"

# Build and push ETo updater image
echo ""
echo "------------------------------------------------------------"
echo "Step 1: Building ETo Updater Image"
echo "------------------------------------------------------------"
docker build -f Dockerfile.update_eto \
    -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/agriguard-repo/eto-updater:latest .

if [ $? -ne 0 ]; then
    echo "❌ ETo image build failed"
    exit 1
fi

echo "Pushing ETo updater image..."
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/agriguard-repo/eto-updater:latest

if [ $? -ne 0 ]; then
    echo "❌ ETo image push failed"
    exit 1
fi

echo "✓ ETo updater image pushed successfully"

# Build and push Precipitation+Deficit updater image
echo ""
echo "------------------------------------------------------------"
echo "Step 2: Building Precipitation+Deficit Updater Image"
echo "------------------------------------------------------------"
docker build -f Dockerfile.update_pr \
    -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/agriguard-repo/pr-deficit-updater:latest .

if [ $? -ne 0 ]; then
    echo "❌ PR+Deficit image build failed"
    exit 1
fi

echo "Pushing Precipitation+Deficit updater image..."
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/agriguard-repo/pr-deficit-updater:latest

if [ $? -ne 0 ]; then
    echo "❌ PR+Deficit image push failed"
    exit 1
fi

echo "✓ Precipitation+Deficit updater image pushed successfully"

# Create/Update ETo updater job
echo ""
echo "------------------------------------------------------------"
echo "Step 3: Creating ETo Updater Cloud Run Job"
echo "------------------------------------------------------------"
gcloud run jobs create agriguard-eto-updater \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/agriguard-repo/eto-updater:latest \
    --region=${REGION} \
    --memory=4Gi \
    --cpu=2 \
    --task-timeout=2h \
    --max-retries=2 \
    --service-account=${SERVICE_ACCOUNT} \
    --quiet 2>/dev/null

if [ $? -ne 0 ]; then
    echo "Job already exists, updating..."
    gcloud run jobs update agriguard-eto-updater \
        --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/agriguard-repo/eto-updater:latest \
        --region=${REGION} \
        --quiet
fi

echo "✓ ETo updater job ready"

# Create/Update Precipitation+Deficit updater job
echo ""
echo "------------------------------------------------------------"
echo "Step 4: Creating Precipitation+Deficit Updater Cloud Run Job"
echo "------------------------------------------------------------"
gcloud run jobs create agriguard-pr-deficit-updater \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/agriguard-repo/pr-deficit-updater:latest \
    --region=${REGION} \
    --memory=4Gi \
    --cpu=2 \
    --task-timeout=2h \
    --max-retries=2 \
    --service-account=${SERVICE_ACCOUNT} \
    --quiet 2>/dev/null

if [ $? -ne 0 ]; then
    echo "Job already exists, updating..."
    gcloud run jobs update agriguard-pr-deficit-updater \
        --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/agriguard-repo/pr-deficit-updater:latest \
        --region=${REGION} \
        --quiet
fi

echo "✓ Precipitation+Deficit updater job ready"

echo ""
echo "======================================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "======================================================================"
echo ""
echo "📋 Available Jobs:"
echo "   • agriguard-eto-updater"
echo "   • agriguard-pr-deficit-updater"
echo ""
echo "🚀 To run updates manually:"
echo "   gcloud run jobs execute agriguard-eto-updater --region=${REGION}"
echo "   gcloud run jobs execute agriguard-pr-deficit-updater --region=${REGION}"
echo ""
echo "📅 To schedule automated weekly updates (recommended):"
echo ""
echo "   # ETo updates every Monday at 2 AM (Chicago time)"
echo "   gcloud scheduler jobs create http eto-weekly-update \\"
echo "     --location=${REGION} \\"
echo "     --schedule='0 2 * * 1' \\"
echo "     --time-zone='America/Chicago' \\"
echo "     --uri='https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/agriguard-eto-updater:run' \\"
echo "     --http-method=POST \\"
echo "     --oauth-service-account-email=${SERVICE_ACCOUNT}"
echo ""
echo "   # Precipitation+Deficit updates every Monday at 3 AM (Chicago time)"
echo "   gcloud scheduler jobs create http pr-deficit-weekly-update \\"
echo "     --location=${REGION} \\"
echo "     --schedule='0 3 * * 1' \\"
echo "     --time-zone='America/Chicago' \\"
echo "     --uri='https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/agriguard-pr-deficit-updater:run' \\"
echo "     --http-method=POST \\"
echo "     --oauth-service-account-email=${SERVICE_ACCOUNT}"
echo ""
echo "======================================================================"
