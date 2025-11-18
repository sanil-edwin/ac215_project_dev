#!/bin/bash

##############################################################################
# AgriGuard RAG System - Quick Deploy Script
# 
# This script automates the deployment of the RAG chat system to your
# AgriGuard application.
#
# Usage: ./deploy_rag.sh [mode]
#   Modes: local, build, deploy, full
##############################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GCP_PROJECT:-"agriguard-ac215"}
REGION=${GCP_REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"agriguard-api-ms4"}
FRONTEND_SERVICE=${FRONTEND_SERVICE:-"agriguard-frontend-ms4"}
REGISTRY="$REGION-docker.pkg.dev/$PROJECT_ID/agriguard"

##############################################################################
# Helper Functions
##############################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check for required commands
    local missing_commands=()
    
    for cmd in docker gcloud python3 npm; do
        if ! command -v $cmd &> /dev/null; then
            missing_commands+=($cmd)
        fi
    done
    
    if [ ${#missing_commands[@]} -gt 0 ]; then
        log_error "Missing required commands: ${missing_commands[*]}"
        exit 1
    fi
    
    # Check for Google API key
    if [ -z "$GOOGLE_API_KEY" ]; then
        log_warning "GOOGLE_API_KEY not set. RAG system will not work without it."
        log_info "Get your key at: https://makersuite.google.com/app/apikey"
        read -p "Enter your Google API key (or press Enter to skip): " api_key
        if [ -n "$api_key" ]; then
            export GOOGLE_API_KEY="$api_key"
        fi
    fi
    
    log_success "Prerequisites check complete"
}

setup_directories() {
    log_info "Setting up directory structure..."
    
    cd backend-api
    
    # Create directories
    mkdir -p knowledge_base/{pdfs,guides,mcsi_docs}
    mkdir -p chroma_db
    
    log_success "Directories created"
}

install_dependencies() {
    log_info "Installing Python dependencies..."
    
    cd backend-api
    
    # Check if requirements-rag.txt exists
    if [ ! -f "requirements-rag.txt" ]; then
        log_error "requirements-rag.txt not found!"
        log_info "Please copy it from the implementation package"
        exit 1
    fi
    
    # Append RAG requirements to main requirements
    if ! grep -q "langchain" requirements.txt; then
        log_info "Adding RAG dependencies to requirements.txt..."
        cat requirements-rag.txt >> requirements.txt
    fi
    
    # Install in virtual environment if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
        pip install -r requirements.txt
    else
        log_warning "No virtual environment found, installing globally"
        pip install -r requirements.txt
    fi
    
    log_success "Dependencies installed"
}

prepare_knowledge_base() {
    log_info "Preparing knowledge base..."
    
    cd backend-api
    
    # Check for documents
    doc_count=$(find knowledge_base -type f \( -name "*.pdf" -o -name "*.md" -o -name "*.txt" \) | wc -l)
    
    if [ $doc_count -eq 0 ]; then
        log_warning "No documents found in knowledge_base/"
        log_info "Please add at least 5-10 PDF documents before deploying"
        log_info "Copy sample documents from the implementation package"
        
        read -p "Continue anyway? (y/N): " continue_empty
        if [[ ! $continue_empty =~ ^[Yy]$ ]]; then
            exit 0
        fi
    else
        log_success "Found $doc_count documents in knowledge base"
    fi
}

run_document_ingestion() {
    log_info "Running document ingestion..."
    
    cd backend-api
    
    if [ ! -f "ingest_documents.py" ]; then
        log_error "ingest_documents.py not found!"
        log_info "Please copy it from the implementation package"
        exit 1
    fi
    
    python3 ingest_documents.py
    
    # Check if chroma_db was created
    if [ ! -d "chroma_db" ] || [ -z "$(ls -A chroma_db)" ]; then
        log_error "Vector store creation failed!"
        exit 1
    fi
    
    log_success "Document ingestion complete"
}

test_backend_locally() {
    log_info "Testing backend locally..."
    
    cd backend-api
    
    # Start server in background
    uvicorn api_extended:app --host 0.0.0.0 --port 8080 &
    SERVER_PID=$!
    
    # Wait for server to start
    sleep 5
    
    # Test health endpoint
    if curl -s http://localhost:8080/health > /dev/null; then
        log_success "Health endpoint OK"
    else
        log_error "Server failed to start"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    
    # Test chat endpoint
    log_info "Testing chat endpoint..."
    response=$(curl -s -X POST http://localhost:8080/api/chat \
        -H "Content-Type: application/json" \
        -d '{"message":"What is MCSI?","county_fips":"19153"}')
    
    if echo "$response" | grep -q "response"; then
        log_success "Chat endpoint working"
    else
        log_warning "Chat endpoint may have issues"
    fi
    
    # Stop server
    kill $SERVER_PID 2>/dev/null
    
    log_success "Local testing complete"
}

build_backend_image() {
    log_info "Building backend Docker image..."
    
    cd backend-api
    
    # Build image
    docker build -t $REGISTRY/api-rag:latest .
    
    if [ $? -ne 0 ]; then
        log_error "Docker build failed"
        exit 1
    fi
    
    log_success "Backend image built"
}

push_backend_image() {
    log_info "Pushing backend image to registry..."
    
    # Configure docker for GCP
    gcloud auth configure-docker $REGION-docker.pkg.dev --quiet
    
    # Push image
    docker push $REGISTRY/api-rag:latest
    
    if [ $? -ne 0 ]; then
        log_error "Docker push failed"
        exit 1
    fi
    
    log_success "Backend image pushed"
}

deploy_backend() {
    log_info "Deploying backend to Cloud Run..."
    
    # Check if API key is set
    if [ -z "$GOOGLE_API_KEY" ]; then
        log_error "GOOGLE_API_KEY must be set for deployment"
        exit 1
    fi
    
    # Deploy service
    gcloud run deploy $SERVICE_NAME \
        --image=$REGISTRY/api-rag:latest \
        --region=$REGION \
        --platform=managed \
        --allow-unauthenticated \
        --memory=4Gi \
        --cpu=2 \
        --timeout=300 \
        --set-env-vars="GOOGLE_API_KEY=$GOOGLE_API_KEY,GCP_PROJECT=$PROJECT_ID" \
        --max-instances=10 \
        --quiet
    
    if [ $? -ne 0 ]; then
        log_error "Backend deployment failed"
        exit 1
    fi
    
    # Get service URL
    BACKEND_URL=$(gcloud run services describe $SERVICE_NAME \
        --region=$REGION \
        --format='value(status.url)')
    
    log_success "Backend deployed at: $BACKEND_URL"
    
    # Test deployed endpoint
    sleep 5
    log_info "Testing deployed backend..."
    
    if curl -s $BACKEND_URL/health | grep -q "status"; then
        log_success "Deployed backend is healthy"
    else
        log_warning "Backend may need time to start up"
    fi
}

build_frontend() {
    log_info "Building frontend..."
    
    cd frontend-app
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies..."
        npm install
    fi
    
    # Build frontend
    npm run build
    
    if [ $? -ne 0 ]; then
        log_error "Frontend build failed"
        exit 1
    fi
    
    log_success "Frontend built"
}

deploy_frontend() {
    log_info "Building and deploying frontend..."
    
    cd frontend-app
    
    # Get backend URL
    BACKEND_URL=$(gcloud run services describe $SERVICE_NAME \
        --region=$REGION \
        --format='value(status.url)')
    
    # Build Docker image
    docker build -t $REGISTRY/frontend-rag:latest .
    
    # Push image
    docker push $REGISTRY/frontend-rag:latest
    
    # Deploy service
    gcloud run deploy $FRONTEND_SERVICE \
        --image=$REGISTRY/frontend-rag:latest \
        --region=$REGION \
        --platform=managed \
        --allow-unauthenticated \
        --set-env-vars="NEXT_PUBLIC_API_URL=$BACKEND_URL" \
        --quiet
    
    if [ $? -ne 0 ]; then
        log_error "Frontend deployment failed"
        exit 1
    fi
    
    # Get frontend URL
    FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE \
        --region=$REGION \
        --format='value(status.url)')
    
    log_success "Frontend deployed at: $FRONTEND_URL"
}

print_summary() {
    echo ""
    echo "=========================================================================="
    echo -e "${GREEN}AgriGuard RAG Deployment Complete!${NC}"
    echo "=========================================================================="
    echo ""
    echo "Backend API: $BACKEND_URL"
    echo "Frontend UI: $FRONTEND_URL"
    echo ""
    echo "Chat endpoint: $BACKEND_URL/api/chat"
    echo ""
    echo "Test with:"
    echo "  curl -X POST $BACKEND_URL/api/chat \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"message\":\"What is MCSI?\"}'"
    echo ""
    echo "=========================================================================="
}

##############################################################################
# Main Execution
##############################################################################

MODE=${1:-"full"}

case $MODE in
    local)
        log_info "Running local setup and test..."
        check_prerequisites
        setup_directories
        install_dependencies
        prepare_knowledge_base
        run_document_ingestion
        test_backend_locally
        log_success "Local setup complete!"
        ;;
        
    build)
        log_info "Building Docker images..."
        check_prerequisites
        build_backend_image
        push_backend_image
        log_success "Build complete!"
        ;;
        
    deploy)
        log_info "Deploying to Cloud Run..."
        check_prerequisites
        deploy_backend
        deploy_frontend
        print_summary
        ;;
        
    full)
        log_info "Running full deployment pipeline..."
        check_prerequisites
        setup_directories
        install_dependencies
        prepare_knowledge_base
        run_document_ingestion
        build_backend_image
        push_backend_image
        deploy_backend
        build_frontend
        deploy_frontend
        print_summary
        ;;
        
    *)
        log_error "Unknown mode: $MODE"
        echo "Usage: $0 [local|build|deploy|full]"
        echo ""
        echo "Modes:"
        echo "  local  - Setup and test locally"
        echo "  build  - Build and push Docker images"
        echo "  deploy - Deploy to Cloud Run"
        echo "  full   - Complete pipeline (default)"
        exit 1
        ;;
esac

log_success "All done!"
