#!/bin/bash

# AgriGuard Deployment Script
# Deploys MCSI processing, ML training, and serving API to GCP
#
# Usage: ./deploy.sh [component]
#   component: mcsi | training | serving | all (default: all)

set -e  # Exit on error

# =============================================================================
# Configuration
# =============================================================================

PROJECT_ID="agriguard-ac215"
REGION="us-central1"
GCS_BUCKET="agriguard-ac215-data"

# Container image names
MCSI_IMAGE="gcr.io/${PROJECT_ID}/mcsi-processor"
TRAINING_IMAGE="gcr.io/${PROJECT_ID}/model-training"
SERVING_IMAGE="gcr.io/${PROJECT_ID}/model-serving"

# Service account
SERVICE_ACCOUNT="agriguard-service-account@${PROJECT_ID}.iam.gserviceaccount.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Please install Google Cloud SDK."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker."
        exit 1
    fi
    
    # Check authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi
    
    # Set project
    gcloud config set project ${PROJECT_ID}
    
    log_info "Prerequisites OK"
}

# =============================================================================
# Build Functions
# =============================================================================

build_mcsi() {
    log_info "Building MCSI container..."
    
    cd containers/mcsi_processing
    
    docker build -t ${MCSI_IMAGE}:latest -f Dockerfile .
    docker push ${MCSI_IMAGE}:latest
    
    log_info "✓ MCSI container built and pushed"
    cd ../..
}

build_training() {
    log_info "Building training container..."
    
    cd containers/model_training
    
    docker build -t ${TRAINING_IMAGE}:latest -f Dockerfile .
    docker push ${TRAINING_IMAGE}:latest
    
    log_info "✓ Training container built and pushed"
    cd ../..
}

build_serving() {
    log_info "Building serving container..."
    
    cd containers/model_serving
    
    docker build -t ${SERVING_IMAGE}:latest -f Dockerfile .
    docker push ${SERVING_IMAGE}:latest
    
    log_info "✓ Serving container built and pushed"
    cd ../..
}

# =============================================================================
# Deploy Functions
# =============================================================================

deploy_mcsi() {
    log_info "Deploying MCSI as Cloud Run Job..."
    
    # Create Cloud Run Job
    gcloud run jobs create mcsi-weekly-job \
        --image ${MCSI_IMAGE}:latest \
        --region ${REGION} \
        --set-env-vars GCS_BUCKET_NAME=${GCS_BUCKET} \
        --service-account ${SERVICE_ACCOUNT} \
        --memory 4Gi \
        --cpu 2 \
        --max-retries 2 \
        --task-timeout 3600 \
        --quiet \
        || gcloud run jobs update mcsi-weekly-job \
            --image ${MCSI_IMAGE}:latest \
            --region ${REGION} \
            --quiet
    
    # Create Cloud Scheduler job (runs every Monday at 8 AM)
    gcloud scheduler jobs create http mcsi-scheduler \
        --location ${REGION} \
        --schedule "0 8 * * 1" \
        --http-method POST \
        --uri "https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/mcsi-weekly-job:run" \
        --oauth-service-account-email ${SERVICE_ACCOUNT} \
        --quiet \
        || gcloud scheduler jobs update http mcsi-scheduler \
            --location ${REGION} \
            --schedule "0 8 * * 1" \
            --quiet
    
    log_info "✓ MCSI deployed (runs weekly on Mondays at 8 AM)"
    
    # Deploy API endpoint
    gcloud run deploy mcsi-api \
        --image ${MCSI_IMAGE}:latest \
        --region ${REGION} \
        --platform managed \
        --allow-unauthenticated \
        --service-account ${SERVICE_ACCOUNT} \
        --memory 2Gi \
        --cpu 1 \
        --set-env-vars GCS_BUCKET_NAME=${GCS_BUCKET} \
        --quiet
    
    MCSI_URL=$(gcloud run services describe mcsi-api --region ${REGION} --format 'value(status.url)')
    log_info "✓ MCSI API deployed at: ${MCSI_URL}"
}

deploy_training() {
    log_info "Setting up model training pipeline..."
    
    # Training is typically run manually or on a schedule
    # We'll create a Cloud Run Job for it
    
    gcloud run jobs create model-training-job \
        --image ${TRAINING_IMAGE}:latest \
        --region ${REGION} \
        --set-env-vars GCS_BUCKET_NAME=${GCS_BUCKET} \
        --service-account ${SERVICE_ACCOUNT} \
        --memory 8Gi \
        --cpu 4 \
        --max-retries 1 \
        --task-timeout 7200 \
        --quiet \
        || gcloud run jobs update model-training-job \
            --image ${TRAINING_IMAGE}:latest \
            --region ${REGION} \
            --quiet
    
    log_info "✓ Training job created (run manually: gcloud run jobs execute model-training-job --region ${REGION})"
}

deploy_serving() {
    log_info "Deploying serving API..."
    
    gcloud run deploy yield-prediction-api \
        --image ${SERVING_IMAGE}:latest \
        --region ${REGION} \
        --platform managed \
        --allow-unauthenticated \
        --service-account ${SERVICE_ACCOUNT} \
        --memory 4Gi \
        --cpu 2 \
        --set-env-vars GCS_BUCKET_NAME=${GCS_BUCKET} \
        --quiet
    
    SERVING_URL=$(gcloud run services describe yield-prediction-api --region ${REGION} --format 'value(status.url)')
    log_info "✓ Serving API deployed at: ${SERVING_URL}"
}

# =============================================================================
# Test Functions
# =============================================================================

test_mcsi() {
    log_info "Testing MCSI API..."
    
    MCSI_URL=$(gcloud run services describe mcsi-api --region ${REGION} --format 'value(status.url)' 2>/dev/null || echo "")
    
    if [ -z "$MCSI_URL" ]; then
        log_warn "MCSI API not deployed yet"
        return
    fi
    
    # Test health endpoint
    HEALTH=$(curl -s ${MCSI_URL}/health)
    echo "Health check: ${HEALTH}"
    
    # Test MCSI endpoint (example county)
    log_info "Testing MCSI for county 19001..."
    MCSI=$(curl -s "${MCSI_URL}/mcsi/19001")
    echo "MCSI result: ${MCSI}"
}

test_serving() {
    log_info "Testing Serving API..."
    
    SERVING_URL=$(gcloud run services describe yield-prediction-api --region ${REGION} --format 'value(status.url)' 2>/dev/null || echo "")
    
    if [ -z "$SERVING_URL" ]; then
        log_warn "Serving API not deployed yet"
        return
    fi
    
    # Test health endpoint
    HEALTH=$(curl -s ${SERVING_URL}/health)
    echo "Health check: ${HEALTH}"
    
    # Test model info endpoint
    INFO=$(curl -s ${SERVING_URL}/model/info)
    echo "Model info: ${INFO}"
}

# =============================================================================
# Main Deployment Flow
# =============================================================================

deploy_all() {
    log_info "========================================="
    log_info "AgriGuard Full Deployment"
    log_info "========================================="
    
    check_prerequisites
    
    log_info "\n1. Building containers..."
    build_mcsi
    build_training
    build_serving
    
    log_info "\n2. Deploying services..."
    deploy_mcsi
    deploy_training
    deploy_serving
    
    log_info "\n3. Running tests..."
    test_mcsi
    test_serving
    
    log_info "\n========================================="
    log_info "Deployment Complete!"
    log_info "========================================="
    log_info "\nService URLs:"
    log_info "  MCSI API: $(gcloud run services describe mcsi-api --region ${REGION} --format 'value(status.url)' 2>/dev/null || echo 'Not deployed')"
    log_info "  Serving API: $(gcloud run services describe yield-prediction-api --region ${REGION} --format 'value(status.url)' 2>/dev/null || echo 'Not deployed')"
    log_info "\nNext steps:"
    log_info "  1. Run initial training: gcloud run jobs execute model-training-job --region ${REGION}"
    log_info "  2. Test predictions: curl ${SERVING_URL}/predict"
    log_info "  3. Monitor jobs: gcloud run jobs list --region ${REGION}"
}

# =============================================================================
# Main
# =============================================================================

COMPONENT=${1:-all}

case $COMPONENT in
    mcsi)
        check_prerequisites
        build_mcsi
        deploy_mcsi
        test_mcsi
        ;;
    training)
        check_prerequisites
        build_training
        deploy_training
        ;;
    serving)
        check_prerequisites
        build_serving
        deploy_serving
        test_serving
        ;;
    all)
        deploy_all
        ;;
    test)
        test_mcsi
        test_serving
        ;;
    *)
        log_error "Unknown component: $COMPONENT"
        echo "Usage: ./deploy.sh [mcsi|training|serving|test|all]"
        exit 1
        ;;
esac

log_info "Done!"
