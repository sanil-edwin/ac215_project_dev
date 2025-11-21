#!/bin/bash

# Setup script for Google Cloud Platform resources
# Creates service account and grants necessary permissions

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-agriguard-ac215}"
SERVICE_ACCOUNT_NAME="yield-downloader"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
BUCKET_NAME="agriguard-ac215-data"

echo "======================================"
echo "Setting up GCP Resources"
echo "======================================"
echo "Project: ${PROJECT_ID}"
echo "Service Account: ${SERVICE_ACCOUNT_EMAIL}"
echo "Bucket: ${BUCKET_NAME}"
echo "======================================"

# Enable required APIs
echo ""
echo "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    containerregistry.googleapis.com \
    cloudbuild.googleapis.com \
    storage-api.googleapis.com \
    --project=${PROJECT_ID}

# Create service account if it doesn't exist
echo ""
echo "Creating service account..."
if gcloud iam service-accounts describe ${SERVICE_ACCOUNT_EMAIL} --project=${PROJECT_ID} &> /dev/null; then
    echo "✓ Service account already exists"
else
    gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
        --display-name="Yield Downloader Service Account" \
        --description="Service account for downloading and processing corn yield data" \
        --project=${PROJECT_ID}
    echo "✓ Service account created"
fi

# Grant permissions to service account
echo ""
echo "Granting permissions..."

# Storage permissions (to read/write to GCS bucket)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/storage.objectAdmin" \
    --condition=None

# Cloud Run permissions (to run jobs)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/run.invoker" \
    --condition=None

echo "✓ Permissions granted"

# Create GCS bucket if it doesn't exist
echo ""
echo "Checking GCS bucket..."
if gsutil ls gs://${BUCKET_NAME} &> /dev/null; then
    echo "✓ Bucket already exists: gs://${BUCKET_NAME}"
else
    echo "Creating bucket..."
    gsutil mb -p ${PROJECT_ID} -l US gs://${BUCKET_NAME}
    echo "✓ Bucket created: gs://${BUCKET_NAME}"
fi

# Create folder structure in bucket
echo ""
echo "Creating folder structure in bucket..."
echo "" | gsutil cp - gs://${BUCKET_NAME}/data_raw/yields/.gitkeep

echo ""
echo "======================================"
echo "✓ Setup Complete!"
echo "======================================"
echo ""
echo "Service Account: ${SERVICE_ACCOUNT_EMAIL}"
echo "Bucket: gs://${BUCKET_NAME}"
echo "Data location: gs://${BUCKET_NAME}/data_raw/yields/"
echo ""
echo "Next Steps:"
echo "1. Get your NASS API key at: https://quickstats.nass.usda.gov/api"
echo "2. Set API key: export NASS_API_KEY='your_key_here'"
echo "3. Build the Docker image: ./scripts/build.sh"
echo "4. Deploy to Cloud Run: ./scripts/deploy-cloudrun.sh"
echo "5. Run the job: gcloud run jobs execute yield-downloader --region=us-central1"
echo "======================================"
