#!/bin/bash

echo "Container is running!!!"
echo "Architecture: $(uname -m)"

# Quick checks to confirm environment has the right tools installed
echo "Python version: $(python --version)"
echo "UV version: $(uv --version)"

# Activates Python virtual environment inside the container
echo "Activating virtual environment..."
source /.venv/bin/activate

echo "Environment ready! Virtual environment activated."

# Define helper functions for different modes
run_cli() {
    echo "Starting interactive CLI mode..."
    exec /bin/bash
}

run_auto_load() {
    echo "Running FULL PIPELINE for sentence-window method..."
    python rag_cli.py load --collection-name "iowa-agriculture" --method sentence-window --input-dir sample-data
    # read PDFs → chunk → embed → store to DB
    exec /bin/bash
}

# Export functions so they're available in the shell
export -f run_cli
export -f run_auto_load

echo -en "\033[92m
The following commands are available:
    run_cli
        Interactive shell (run CLI commands manually)
    run_auto_load
        Auto-run load command for iowa-agriculture collection
\033[0m
"

# Check DEV environment variable for different modes
if [ "${DEV}" = "1" ]; then
    # DEV=1: Interactive shell (default)
    run_cli
elif [ "${DEV}" = "2" ]; then
    # DEV=2: Reserved for future API server mode
    echo "DEV=2 mode not yet implemented (reserved for FastAPI server)"
    run_cli
elif [ "${DEV}" = "3" ]; then
    # DEV=3: Auto-run load command
    run_auto_load
else
    # Default: Interactive shell
    run_cli
fi