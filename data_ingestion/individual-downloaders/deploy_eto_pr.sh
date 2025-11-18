#!/bin/bash
# Quick deployment script for ETo and Precipitation Cloud Run Jobs
# AgriGuard AC215 Project

set -e  # Exit on error

# Configuration
PROJECT_ID="agriguard-ac215"
REGION="us-central1"
REPO_NAME="agriguard-repo"
SERVICE_ACCOUNT="agriguard-service-account@${PROJECT_ID}.iam.gserviceaccount.com"

echo "============================================================"
echo "AgriGuard ETo & Precipitation Deployment"
echo "============================================================"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo ""

# Function to build and push image
build_and_push() {
    local indicator=$1
    local dockerfile=$2
    
    echo "------------------------------------------------------------"
    echo "Building ${indicator} image..."
    echo "------------------------------------------------------------"
    
    IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${indicator,,}-corn-downloader:latest"
    
    docker build -f ${dockerfile} -t ${IMAGE_URI} .
    docker push ${IMAGE_URI}
    
    echo "✓ ${indicator} image pushed successfully"
}

# Function to create jobs for all years
create_jobs() {
    local indicator=$1
    local image_uri=$2
    
    echo "------------------------------------------------------------"
    echo "Creating ${indicator} Cloud Run Jobs (2016-2025)..."
    echo "------------------------------------------------------------"
    
    for YEAR in {2016..2025}; do
        JOB_NAME="agriguard-${indicator,,}-${YEAR}"
        
        # Check if job already exists
        if gcloud run jobs describe ${JOB_NAME} --region=${REGION} &>/dev/null; then
            echo "  Job ${JOB_NAME} already exists, skipping..."
        else
            gcloud run jobs create ${JOB_NAME} \
                --image=${image_uri} \
                --region=${REGION} \
                --memory=4Gi \
                --cpu=2 \
                --task-timeout=2h \
                --max-retries=2 \
                --service-account=${SERVICE_ACCOUNT} \
                --set-env-vars=YEAR=${YEAR} \
                --quiet
            
            echo "  ✓ Created ${JOB_NAME}"
        fi
    done
}

# Function to execute all jobs
execute_jobs() {
    local indicator=$1
    
    echo "------------------------------------------------------------"
    echo "Executing ${indicator} jobs (all years in parallel)..."
    echo "------------------------------------------------------------"
    
    for YEAR in {2016..2025}; do
        JOB_NAME="agriguard-${indicator,,}-${YEAR}"
        gcloud run jobs execute ${JOB_NAME} --region=${REGION} --quiet &
        echo "  Started ${JOB_NAME}"
    done
    
    echo "  Waiting for all ${indicator} jobs to complete..."
    wait
    echo "  ✓ All ${indicator} jobs completed"
}

# Main menu
echo "What would you like to do?"
echo "1) Build and push Docker images only"
echo "2) Create Cloud Run Jobs only"
echo "3) Execute all jobs (download data)"
echo "4) Full deployment (build + create + execute)"
echo "5) Execute current year only (for updates)"
echo "6) Exit"
echo ""
read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        echo ""
        echo "Building and pushing Docker images..."
        build_and_push "ETo" "Dockerfile.eto"
        build_and_push "Precipitation" "Dockerfile.pr"
        echo ""
        echo "✅ Images built and pushed successfully!"
        ;;
    2)
        echo ""
        ETO_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/eto-corn-downloader:latest"
        PR_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/pr-corn-downloader:latest"
        
        create_jobs "eto" "${ETO_IMAGE}"
        create_jobs "pr" "${PR_IMAGE}"
        echo ""
        echo "✅ Cloud Run Jobs created successfully!"
        ;;
    3)
        echo ""
        echo "This will execute 20 jobs (10 ETo + 10 Precipitation)"
        echo "Estimated time: 1-2 hours"
        echo "Estimated cost: ~$5-6"
        echo ""
        read -p "Continue? (y/n): " confirm
        
        if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
            execute_jobs "eto"
            execute_jobs "pr"
            echo ""
            echo "✅ All jobs executed successfully!"
            echo ""
            echo "Next steps:"
            echo "1. Run: python3 merge_eto.py"
            echo "2. Run: python3 merge_pr.py"
        fi
        ;;
    4)
        echo ""
        echo "FULL DEPLOYMENT"
        echo "This will:"
        echo "  1. Build and push Docker images"
        echo "  2. Create 20 Cloud Run Jobs"
        echo "  3. Execute all jobs to download data (2016-2025)"
        echo ""
        echo "Estimated time: 2-3 hours"
        echo "Estimated cost: ~$5-6"
        echo ""
        read -p "Continue with full deployment? (y/n): " confirm
        
        if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
            # Step 1: Build images
            build_and_push "ETo" "Dockerfile.eto"
            build_and_push "Precipitation" "Dockerfile.pr"
            
            # Step 2: Create jobs
            ETO_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/eto-corn-downloader:latest"
            PR_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/pr-corn-downloader:latest"
            
            create_jobs "eto" "${ETO_IMAGE}"
            create_jobs "pr" "${PR_IMAGE}"
            
            # Step 3: Execute jobs
            execute_jobs "eto"
            execute_jobs "pr"
            
            echo ""
            echo "============================================================"
            echo "✅ FULL DEPLOYMENT COMPLETE!"
            echo "============================================================"
            echo ""
            echo "Next steps:"
            echo "1. Run: python3 merge_eto.py"
            echo "2. Run: python3 merge_pr.py"
            echo "3. Validate data in GCS:"
            echo "   - gs://agriguard-ac215-data/data_raw_new/weather/eto/"
            echo "   - gs://agriguard-ac215-data/data_raw_new/weather/pr/"
        fi
        ;;
    5)
        echo ""
        CURRENT_YEAR=$(date +%Y)
        echo "Executing jobs for current year: ${CURRENT_YEAR}"
        echo ""
        
        gcloud run jobs execute agriguard-eto-${CURRENT_YEAR} --region=${REGION} &
        gcloud run jobs execute agriguard-pr-${CURRENT_YEAR} --region=${REGION} &
        wait
        
        echo ""
        echo "✅ Current year jobs completed!"
        echo ""
        echo "Next steps:"
        echo "1. Run: python3 merge_eto.py"
        echo "2. Run: python3 merge_pr.py"
        ;;
    6)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice. Exiting..."
        exit 1
        ;;
esac

echo ""
echo "============================================================"
echo "Script completed successfully!"
echo "============================================================"
