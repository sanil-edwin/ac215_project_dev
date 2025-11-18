#!/bin/bash

###############################################################################
# Deployment Verification Script
###############################################################################

set -e

echo "Verifying AgriGuard Deployment..."
echo ""

# Check file structure
echo "Checking file structure..."
REQUIRED_FILES=(
    "src/mcsi_calculator.py"
    "src/feature_builder.py"
    "src/train_model.py"
    "src/api.py"
    "tests/test_mcsi_calculator.py"
    "tests/test_feature_builder.py"
    "containers/mcsi_processing/Dockerfile"
    "containers/model_training/Dockerfile"
    "containers/model_serving/Dockerfile"
    "requirements.txt"
    "deploy.sh"
)

MISSING_FILES=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file (MISSING)"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

echo ""
if [ $MISSING_FILES -eq 0 ]; then
    echo "✓ All required files present"
else
    echo "Warning: $MISSING_FILES files missing"
fi

# Check Python environment
echo ""
echo "Checking Python environment..."
if [ -d "venv" ]; then
    echo "✓ Virtual environment exists"
    
    # Try to activate and check packages
    source venv/bin/activate || . venv/Scripts/activate
    
    REQUIRED_PACKAGES=("pandas" "numpy" "lightgbm" "fastapi" "pytest")
    for pkg in "${REQUIRED_PACKAGES[@]}"; do
        if python -c "import $pkg" 2>/dev/null; then
            echo "✓ $pkg installed"
        else
            echo "✗ $pkg not installed"
        fi
    done
else
    echo "✗ Virtual environment not found"
fi

# Check GCP configuration
echo ""
echo "Checking GCP configuration..."
if command -v gcloud &> /dev/null; then
    echo "✓ gcloud CLI installed"
    PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [ -n "$PROJECT" ]; then
        echo "✓ GCP project: $PROJECT"
    else
        echo "Warning: No GCP project configured"
    fi
else
    echo "✗ gcloud CLI not installed"
fi

# Check Docker
echo ""
echo "Checking Docker..."
if command -v docker &> /dev/null; then
    echo "✓ Docker installed"
    if docker ps &> /dev/null; then
        echo "✓ Docker daemon running"
    else
        echo "Warning: Docker daemon not running"
    fi
else
    echo "✗ Docker not installed"
fi

echo ""
echo "Verification complete!"
