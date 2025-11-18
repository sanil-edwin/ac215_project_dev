# View Cloud Run job status and logs

param(
    [Parameter(Position=0)]
    [ValidateSet('status', 'logs', 'list', 'execute', 'help')]
    [string]$Command = "status",
    
    [string]$ProjectId = "agriguard-ac215",
    [string]$Region = "us-central1",
    [string]$JobName = "mask-downloader"
)

function Show-Help {
    Write-Host ""
    Write-Host "Mask Downloader - Log Viewer and Status Checker" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\View-Status.ps1 [COMMAND]" -ForegroundColor White
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Cyan
    Write-Host "  status      Show current job status and recent executions" -ForegroundColor White
    Write-Host "  logs        View logs from the most recent execution" -ForegroundColor White
    Write-Host "  list        List all executions" -ForegroundColor White
    Write-Host "  execute     Execute the job now" -ForegroundColor White
    Write-Host "  help        Show this help message" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\View-Status.ps1 status" -ForegroundColor White
    Write-Host "  .\View-Status.ps1 logs" -ForegroundColor White
    Write-Host "  .\View-Status.ps1 execute" -ForegroundColor White
    Write-Host ""
}

function Show-Status {
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Mask Downloader Job Status" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Job Configuration:" -ForegroundColor Yellow
    gcloud run jobs describe $JobName `
        --region=$Region `
        --project=$ProjectId `
        --format="table(
            name,
            region,
            status.conditions[0].status:label=READY,
            status.conditions[0].reason:label=REASON
        )"
    
    Write-Host ""
    Write-Host "Recent Executions:" -ForegroundColor Yellow
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
    $executionId = gcloud run jobs executions list `
        --job=$JobName `
        --region=$Region `
        --project=$ProjectId `
        --limit=1 `
        --format="value(name)" 2>$null
    
    if (-not $executionId) {
        Write-Host "No executions found for job $JobName" -ForegroundColor Yellow
        return
    }
    
    Write-Host "Showing logs for execution: $executionId" -ForegroundColor Yellow
    Write-Host ""
    
    gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=$JobName AND resource.labels.location=$Region" `
        --limit=100 `
        --format="table(timestamp, severity, jsonPayload.message)" `
        --project=$ProjectId
}

function List-Executions {
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
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Job execution started" -ForegroundColor Green
        Write-Host ""
        Write-Host "To view status: .\View-Status.ps1 status" -ForegroundColor Cyan
        Write-Host "To view logs: .\View-Status.ps1 logs" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "✗ Failed to execute job" -ForegroundColor Red
    }
}

# Main command handling
switch ($Command) {
    "status" {
        Show-Status
    }
    "logs" {
        Show-Logs
    }
    "list" {
        List-Executions
    }
    "execute" {
        Execute-Job
    }
    "help" {
        Show-Help
    }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Show-Help
        exit 1
    }
}
