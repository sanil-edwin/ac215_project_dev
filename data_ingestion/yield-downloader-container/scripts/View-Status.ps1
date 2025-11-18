# Utility script for viewing Cloud Run job logs and status

param(
    [Parameter(Position=0)]
    [ValidateSet('status', 'logs', 'list', 'execute', 'help')]
    [string]$Command = 'status',
    
    [string]$ProjectId = $env:GCP_PROJECT_ID,
    [string]$Region = "us-central1",
    [string]$JobName = "yield-downloader"
)

if (-not $ProjectId) {
    $ProjectId = "agriguard-ac215"
}

function Show-Help {
    Write-Host @"
Yield Downloader - Log Viewer and Status Checker

Usage: .\View-Status.ps1 [COMMAND]

Commands:
    status      Show current job status and recent executions
    logs        View logs from the most recent execution
    list        List all executions
    execute     Execute the job now
    help        Show this help message

Examples:
    .\View-Status.ps1 status
    .\View-Status.ps1 logs
    .\View-Status.ps1 execute

"@
}

function Show-Status {
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Yield Downloader Job Status" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Job Configuration:"
    gcloud run jobs describe $JobName `
        --region=$Region `
        --project=$ProjectId `
        --format="table(
            name,
            region,
            status.conditions[0].status:label=READY,
            status.conditions[0].reason:label=REASON
        )"
    
    Write-Host "`nRecent Executions:"
    gcloud run jobs executions list `
        --job=$JobName `
        --region=$Region `
        --project=$ProjectId `
        --limit=5 `
        --format="table(
            name,
            status.conditions[0].type:label=STATUS,
            status.startTime.date('%Y-%m-%d %H:%M:%S'):label=STARTED,
            status.completionTime.date('%Y-%m-%d %H:%M:%S'):label=COMPLETED
        )"
}

function Show-Logs {
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Recent Logs" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Get the most recent execution
    $ExecutionId = gcloud run jobs executions list `
        --job=$JobName `
        --region=$Region `
        --project=$ProjectId `
        --limit=1 `
        --format="value(name)" 2>$null
    
    if (-not $ExecutionId) {
        Write-Host "No executions found for job $JobName" -ForegroundColor Yellow
        return
    }
    
    Write-Host "Showing logs for execution: $ExecutionId`n"
    
    gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=$JobName AND resource.labels.location=$Region" `
        --limit=100 `
        --format="table(timestamp, severity, jsonPayload.message)" `
        --project=$ProjectId
}

function Show-List {
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "All Executions" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""
    
    gcloud run jobs executions list `
        --job=$JobName `
        --region=$Region `
        --project=$ProjectId `
        --format="table(
            name,
            status.conditions[0].type:label=STATUS,
            status.startTime.date('%Y-%m-%d %H:%M:%S'):label=STARTED,
            status.completionTime.date('%Y-%m-%d %H:%M:%S'):label=COMPLETED,
            status.succeededCount:label=SUCCESS,
            status.failedCount:label=FAILED
        )"
}

function Execute-Job {
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Executing Job" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""
    
    gcloud run jobs execute $JobName `
        --region=$Region `
        --project=$ProjectId
    
    Write-Host "`n✓ Job execution started" -ForegroundColor Green
    Write-Host ""
    Write-Host "To view status: .\View-Status.ps1 status"
    Write-Host "To view logs: .\View-Status.ps1 logs"
}

# Main command handling
switch ($Command) {
    'status' { Show-Status }
    'logs' { Show-Logs }
    'list' { Show-List }
    'execute' { Execute-Job }
    'help' { Show-Help }
    default {
        Write-Host "Unknown command: $Command`n" -ForegroundColor Red
        Show-Help
    }
}
