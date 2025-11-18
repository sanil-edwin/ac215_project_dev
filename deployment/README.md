# Deployment Scripts

**One-command deployment to Google Cloud Run**

## Files

- `deploy.sh` - Deploys both backend and frontend
- `test_api.sh` - Tests API endpoints

## Prerequisites

1. Google Cloud SDK configured
2. Docker installed and running
3. Models in `../backend-api/models/`
4. Authenticated: `gcloud auth login`

## Deploy Everything

```bash
./deploy.sh
```

This will:
1. Build backend container
2. Push to Artifact Registry
3. Deploy backend to Cloud Run
4. Get backend URL
5. Build frontend with backend URL
6. Deploy frontend to Cloud Run
7. Display both URLs

**Time:** 30-45 minutes

## Test Deployment

```bash
./test_api.sh
```

Tests all 5 API endpoints.

## Manual Deploy

If script fails, see deployment commands in:
- `../DEPLOY.md`
- `../COMMANDS.md`

## Output

After deployment:
- Backend API URL
- Frontend URL  
- Saved to `deployment_urls.txt`
