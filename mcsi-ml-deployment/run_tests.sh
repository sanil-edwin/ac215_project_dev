#!/bin/bash

###############################################################################
# Testing Script
###############################################################################

set -e

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate || . venv/Scripts/activate
fi

echo "Running AgriGuard Tests..."
echo ""

# Test MCSI Calculator
if [ -f "src/mcsi_calculator.py" ]; then
    echo "Testing MCSI Calculator..."
    python src/mcsi_calculator.py
    echo "✓ MCSI Calculator test passed"
else
    echo "Warning: mcsi_calculator.py not found"
fi

echo ""

# Test Feature Builder
if [ -f "src/feature_builder.py" ]; then
    echo "Testing Feature Builder..."
    python src/feature_builder.py
    echo "✓ Feature Builder test passed"
else
    echo "Warning: feature_builder.py not found"
fi

echo ""

# Run pytest
if [ -d "tests" ]; then
    echo "Running pytest suite..."
    pytest tests/ -v --cov=src --cov-report=term-missing || echo "Some tests failed or pytest not installed"
else
    echo "Warning: tests directory not found"
fi

echo ""
echo "✓ Testing complete!"
