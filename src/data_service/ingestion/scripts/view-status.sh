#!/bin/bash

# Utility script for viewing Cloud Run job logs and status

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-agriguard-ac215}"
REGION="${REGION:-us-central1}"
JOB_NAME="yield-downloader"

function show_help() {
    cat << EOF
Yield Downloader - Log Viewer and Status Checker

Usage: $0 [COMMAND]

Commands:
    status      Show current job status and recent executions
    logs        View logs from the most recent execution
    list        List all executions
    execute     Execute the job now
    help        Show this help message

Examples:
    $0 status
    $0 logs
    $0 execute

EOF
}

function show_status() {
    echo "======================================"
    echo "Yield Downloader Job Status"
    echo "======================================"
    echo ""
    
    echo "Job Configuration:"
    gcloud run jobs describe ${JOB_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --format="table(
            name,
            region,
            status.conditions[0].status:label=READY,
            status.conditions[0].reason:label=REASON
        )"
    
    echo ""
    echo "Recent Executions:"
    gcloud run jobs executions list \
        --job=${JOB_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --limit=5 \
        --format="table(
            name,
            status.conditions[0].type:label=STATUS,
            status.startTime.date('%Y-%m-%d %H:%M:%S'):label=STARTED,
            status.completionTime.date('%Y-%m-%d %H:%M:%S'):label=COMPLETED
        )"
}

function show_logs() {
    echo "======================================"
    echo "Recent Logs"
    echo "======================================"
    echo ""
    
    # Get the most recent execution
    EXECUTION_ID=$(gcloud run jobs executions list \
        --job=${JOB_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --limit=1 \
        --format="value(name)")
    
    if [ -z "$EXECUTION_ID" ]; then
        echo "No executions found for job ${JOB_NAME}"
        exit 1
    fi
    
    echo "Showing logs for execution: ${EXECUTION_ID}"
    echo ""
    
    gcloud logging read "resource.type=cloud_run_job \
        AND resource.labels.job_name=${JOB_NAME} \
        AND resource.labels.location=${REGION}" \
        --limit=100 \
        --format="table(timestamp, severity, jsonPayload.message)" \
        --project=${PROJECT_ID}
}

function list_executions() {
    echo "======================================"
    echo "All Executions"
    echo "======================================"
    echo ""
    
    gcloud run jobs executions list \
        --job=${JOB_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --format="table(
            name,
            status.conditions[0].type:label=STATUS,
            status.startTime.date('%Y-%m-%d %H:%M:%S'):label=STARTED,
            status.completionTime.date('%Y-%m-%d %H:%M:%S'):label=COMPLETED,
            status.succeededCount:label=SUCCESS,
            status.failedCount:label=FAILED
        )"
}

function execute_job() {
    echo "======================================"
    echo "Executing Job"
    echo "======================================"
    echo ""
    
    gcloud run jobs execute ${JOB_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID}
    
    echo ""
    echo "✓ Job execution started"
    echo ""
    echo "To view status: $0 status"
    echo "To view logs: $0 logs"
}

# Main command handling
case "${1:-status}" in
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    list)
        list_executions
        ;;
    execute)
        execute_job
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
