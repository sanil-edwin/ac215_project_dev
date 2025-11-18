#!/bin/bash

###############################################################################
# Automated File Organization Script
# Run this after placing all files in prep/ folder
###############################################################################

set -e

PREP="../prep"
DEPLOY="."

echo "Starting file organization..."

# Check if prep folder exists
if [ ! -d "$PREP" ]; then
    echo "ERROR: prep folder not found at $PREP"
    echo "Please ensure prep folder is at: C:\Users\artyb\OneDrive\Documents\PERSONAL\HES\AC215_E115\Project\agriguard\AgriGuard\prep"
    exit 1
fi

echo "✓ Found prep folder"

# Copy documentation
echo "Copying documentation..."
cp $PREP/*.md docs/ 2>/dev/null || echo "Warning: Some .md files not found"
cp $PREP/WINDOWS_SETUP_SUMMARY.txt docs/ 2>/dev/null || true
cp $PREP/FILE_ORGANIZATION_GUIDE.txt docs/ 2>/dev/null || true

# Copy root files
echo "Copying root files..."
cp $PREP/requirements.txt . 2>/dev/null || echo "Warning: requirements.txt not found"
cp $PREP/requirements-test.txt . 2>/dev/null || echo "Warning: requirements-test.txt not found"
cp $PREP/deploy.sh . 2>/dev/null || echo "Warning: deploy.sh not found"
chmod +x deploy.sh 2>/dev/null || true

# Copy source code
echo "Copying source code..."
cp $PREP/mcsi_calculator.py src/ 2>/dev/null || echo "Warning: mcsi_calculator.py not found"
cp $PREP/feature_builder.py src/ 2>/dev/null || echo "Warning: feature_builder.py not found"
cp $PREP/train_model.py src/ 2>/dev/null || echo "Warning: train_model.py not found"
cp $PREP/api.py src/ 2>/dev/null || echo "Warning: api.py not found"

# Copy tests
echo "Copying tests..."
cp $PREP/test_mcsi_calculator.py tests/ 2>/dev/null || echo "Warning: test_mcsi_calculator.py not found"
cp $PREP/test_feature_builder.py tests/ 2>/dev/null || echo "Warning: test_feature_builder.py not found"

# Copy and rename Dockerfiles
echo "Copying Dockerfiles..."
cp $PREP/Dockerfile.mcsi containers/mcsi_processing/Dockerfile 2>/dev/null || echo "Warning: Dockerfile.mcsi not found"
cp $PREP/Dockerfile.training containers/model_training/Dockerfile 2>/dev/null || echo "Warning: Dockerfile.training not found"
cp $PREP/Dockerfile.serving containers/model_serving/Dockerfile 2>/dev/null || echo "Warning: Dockerfile.serving not found"

# Copy container sources
echo "Copying container sources..."
cp src/mcsi_calculator.py containers/mcsi_processing/src/ 2>/dev/null || true
cp requirements.txt containers/mcsi_processing/ 2>/dev/null || true

cp src/feature_builder.py containers/model_training/src/ 2>/dev/null || true
cp src/train_model.py containers/model_training/src/ 2>/dev/null || true
cp requirements.txt containers/model_training/ 2>/dev/null || true

cp src/api.py containers/model_serving/src/ 2>/dev/null || true
cp src/mcsi_calculator.py containers/model_serving/src/ 2>/dev/null || true
cp requirements.txt containers/model_serving/ 2>/dev/null || true

echo ""
echo "✓ File organization complete!"
echo ""
echo "Next steps:"
echo "1. Review FILE_PLACEMENT_GUIDE.txt"
echo "2. Verify all files are in place"
echo "3. Run: bash setup_python_env.sh"
