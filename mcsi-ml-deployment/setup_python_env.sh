#!/bin/bash

###############################################################################
# Python Environment Setup Script
###############################################################################

set -e

echo "Setting up Python environment..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate || . venv/Scripts/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
    echo "✓ Dependencies installed"
else
    echo "Warning: requirements.txt not found"
fi

# Install test dependencies
if [ -f "requirements-test.txt" ]; then
    echo "Installing test dependencies..."
    pip install -r requirements-test.txt
    echo "✓ Test dependencies installed"
else
    echo "Warning: requirements-test.txt not found"
fi

echo ""
echo "✓ Python environment setup complete!"
echo ""
echo "To activate the environment:"
echo "  Linux/Mac: source venv/bin/activate"
echo "  Windows:   venv\\Scripts\\activate"
