#!/bin/bash

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Save current directory
ROOT_DIR=$(pwd)

log_info "Starting RAG deployment from: $ROOT_DIR"

# Check backend-api exists
if [ ! -d "$ROOT_DIR/backend-api" ]; then
    log_error "backend-api directory not found!"
    exit 1
fi

# Check if RAG files exist
log_info "Checking RAG files..."
if [ ! -f "$ROOT_DIR/backend-api/ingest_documents.py" ]; then
    log_error "ingest_documents.py not found in backend-api/"
    exit 1
fi

if [ ! -f "$ROOT_DIR/backend-api/rag_chat.py" ]; then
    log_error "rag_chat.py not found in backend-api/"
    exit 1
fi

log_success "RAG files found"

# Create knowledge base if doesn't exist
log_info "Setting up knowledge base..."
mkdir -p "$ROOT_DIR/backend-api/knowledge_base/"{pdfs,guides,mcsi_docs}
log_success "Knowledge base directories ready"

# Check for documents
doc_count=$(find "$ROOT_DIR/backend-api/knowledge_base" -type f \( -name "*.pdf" -o -name "*.md" -o -name "*.txt" \) 2>/dev/null | wc -l)
log_info "Found $doc_count documents in knowledge base"

if [ $doc_count -eq 0 ]; then
    log_error "No documents found! Add PDFs/docs to backend-api/knowledge_base/"
    log_info "You can continue, but RAG won't have any knowledge..."
    read -p "Continue anyway? (y/N): " continue_empty
    if [[ ! $continue_empty =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Install dependencies
log_info "Installing Python dependencies..."
cd "$ROOT_DIR/backend-api"

if [ ! -f "requirements.txt" ]; then
    log_error "requirements.txt not found!"
    exit 1
fi

# Check if RAG dependencies already in requirements
if ! grep -q "langchain" requirements.txt; then
    log_info "Adding RAG dependencies to requirements.txt..."
    if [ -f "requirements-rag.txt" ]; then
        cat requirements-rag.txt >> requirements.txt
        log_success "RAG dependencies added"
    else
        log_error "requirements-rag.txt not found!"
        exit 1
    fi
fi

# Install (in virtual env if exists)
if [ -d "venv" ]; then
    log_info "Installing in virtual environment..."
    source venv/bin/activate
    pip install -r requirements.txt --quiet
else
    log_info "No virtual environment found, installing globally..."
    pip install -r requirements.txt --quiet
fi

log_success "Dependencies installed"

# Run document ingestion
log_info "Running document ingestion..."
python3 ingest_documents.py

if [ ! -d "chroma_db" ] || [ -z "$(ls -A chroma_db 2>/dev/null)" ]; then
    log_error "Vector store creation failed!"
    exit 1
fi

log_success "Vector store created successfully"

cd "$ROOT_DIR"
log_success "RAG system setup complete!"

echo ""
echo "=========================================="
echo "Next steps:"
echo "=========================================="
echo "1. Set your Google API key:"
echo "   export GOOGLE_API_KEY='your-key-here'"
echo ""
echo "2. Update backend-api/api_extended.py to add:"
echo "   - Import rag_chat module"
echo "   - Initialize RAG in startup()"
echo "   - Add /api/chat endpoint"
echo ""
echo "3. Test locally:"
echo "   cd backend-api"
echo "   uvicorn api_extended:app --reload"
echo ""
echo "4. Build and deploy to Cloud Run"
echo "=========================================="
