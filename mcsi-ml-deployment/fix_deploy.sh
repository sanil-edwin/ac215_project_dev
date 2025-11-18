#!/bin/bash
# Fix deploy.sh to use Artifact Registry
sed -i 's|IMAGE_PREFIX="gcr.io/agriguard-ac215"|IMAGE_PREFIX="us-central1-docker.pkg.dev/agriguard-ac215/agriguard"|g' deploy.sh
echo "Fixed deploy.sh to use Artifact Registry"
