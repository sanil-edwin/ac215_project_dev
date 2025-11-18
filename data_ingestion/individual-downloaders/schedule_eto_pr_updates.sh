#!/bin/bash
# Schedule Weekly ETo & Precipitation Updates (May-October)
set -e

PROJECT_ID="agriguard-ac215"
REGION="us-central1"
SERVICE_ACCOUNT="723493210689-compute@developer.gserviceaccount.com"

echo "Scheduling weekly ETo, Precipitation & Water Deficit updates..."

# ETo - Every Monday at 3 AM CT during May-October
gcloud scheduler jobs create http agriguard-schedule-update-eto \
  --location=${REGION} \
  --schedule="0 3 * 5-10 1" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/agriguard-update-eto:run" \
  --http-method=POST \
  --oauth-service-account-email=${SERVICE_ACCOUNT} \
  --time-zone="America/Chicago" \
  --description="Weekly ETo update (May-Oct, Mondays 3AM)" \
  || gcloud scheduler jobs update http agriguard-schedule-update-eto \
       --location=${REGION} \
       --schedule="0 3 * 5-10 1" \
       --time-zone="America/Chicago"

echo "✓ ETo scheduled: Mondays 3 AM (May-Oct)"

# Precipitation + Water Deficit - Every Monday at 4 AM CT during May-October
gcloud scheduler jobs create http agriguard-schedule-update-pr \
  --location=${REGION} \
  --schedule="0 4 * 5-10 1" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/agriguard-update-pr:run" \
  --http-method=POST \
  --oauth-service-account-email=${SERVICE_ACCOUNT} \
  --time-zone="America/Chicago" \
  --description="Weekly Precipitation + Water Deficit update (May-Oct, Mondays 4AM)" \
  || gcloud scheduler jobs update http agriguard-schedule-update-pr \
       --location=${REGION} \
       --schedule="0 4 * 5-10 1" \
       --time-zone="America/Chicago"

echo "✓ Precipitation + Water Deficit scheduled: Mondays 4 AM (May-Oct)"

echo ""
echo "✅ Scheduling complete!"
echo ""
echo "Schedule: Every Monday, 3-4 AM CT, May through October"
echo "  3 AM - ETo update"
echo "  4 AM - Precipitation + Water Deficit update"
echo ""
echo "Test run:"
echo "  gcloud scheduler jobs run agriguard-schedule-update-eto --location=${REGION}"
echo "  gcloud scheduler jobs run agriguard-schedule-update-pr --location=${REGION}"
echo ""
echo "View schedules:"
echo "  gcloud scheduler jobs list --location=${REGION} | grep update"
