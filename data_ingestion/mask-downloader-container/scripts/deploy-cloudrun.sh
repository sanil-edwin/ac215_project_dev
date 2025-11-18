#!/bin/bash

# Deploy mask downloader to Google Cloud Run as a Job
# Cloud Run Jobs are ideal for batch processing tasks like data downloads

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-agriguard-ac215}"
IMAGE_NAME="mask-downloader"
VERSION="${VERSION:-latest}"
REGION="${REGION:-us-central1}"
JOB_NAME="mask-downloader"
SERVICE_ACCOUNT="mask-downloader@${PROJECT_ID}.iam.gserviceaccount.com"

# Full image name
FULL_IMAGE_NAME="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${VERSION}"

echo "======================================"
echo "Deploying to Google Cloud Run Job"
echo "======================================"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Job: ${JOB_NAME}"
echo "Image: ${FULL_IMAGE_NAME}"
echo "======================================"

# Check if job already exists
if gcloud run jobs describe ${JOB_NAME} --region=${REGION} --project=${PROJECT_ID} &> /dev/null; then
    echo "Updating existing Cloud Run Job..."
    gcloud run jobs update ${JOB_NAME} \
        --image=${FULL_IMAGE_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --set-env-vars="GCS_BUCKET_NAME=agriguard-ac215-data,START_YEAR=2010" \
        --memory=4Gi \
        --cpu=2 \
        --max-retries=1 \
        --task-timeout=3600 \
        --service-account=${SERVICE_ACCOUNT}
else
    echo "Creating new Cloud Run Job..."
    gcloud run jobs create ${JOB_NAME} \
        --image=${FULL_IMAGE_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --set-env-vars="GCS_BUCKET_NAME=agriguard-ac215-data,START_YEAR=2010" \
        --memory=4Gi \
        --cpu=2 \
        --max-retries=1 \
        --task-timeout=3600 \
        --service-account=${SERVICE_ACCOUNT}
fi

echo ""
echo "✓ Deployment complete!"
echo ""
echo "======================================"
echo "Next Steps:"
echo "======================================"
echo "1. Run the job:"
echo "   gcloud run jobs execute ${JOB_NAME} --region=${REGION}"
echo ""
echo "2. Check job status:"
echo "   gcloud run jobs executions list --job=${JOB_NAME} --region=${REGION}"
echo ""
echo "3. View logs:"
echo "   gcloud run jobs executions describe EXECUTION_ID --region=${REGION}"
echo ""
echo "4. Schedule with Cloud Scheduler (optional):"
echo "   gcloud scheduler jobs create http mask-downloader-schedule \\"
echo "     --location=${REGION} \\"
echo "     --schedule='0 0 1 * *' \\"
echo "     --uri='https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run' \\"
echo "     --http-method=POST \\"
echo "     --oauth-service-account-email=${SERVICE_ACCOUNT}"
echo "======================================"
