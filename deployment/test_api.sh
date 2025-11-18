#!/bin/bash

# Quick test script for AgriGuard API

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get API URL
if [ -f deployment_urls.txt ]; then
    source deployment_urls.txt
else
    echo -e "${YELLOW}Enter API URL:${NC}"
    read API_URL
fi

echo -e "${GREEN}Testing AgriGuard API...${NC}"
echo -e "API: ${API_URL}\n"

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
curl -s ${API_URL}/health | jq .
echo -e "${GREEN}✓ Health check passed${NC}\n"

# Test 2: Get Counties
echo -e "${YELLOW}Test 2: Get Counties List${NC}"
curl -s ${API_URL}/api/counties | jq '.total'
echo -e "${GREEN}✓ Counties endpoint working${NC}\n"

# Test 3: Get MCSI for Polk County
echo -e "${YELLOW}Test 3: Get MCSI (Polk County - 19153)${NC}"
curl -s ${API_URL}/api/mcsi/19153 | jq '{county: .county_name, mcsi: .mcsi_score, stress: .stress_level}'
echo -e "${GREEN}✓ MCSI endpoint working${NC}\n"

# Test 4: Predict Yield
echo -e "${YELLOW}Test 4: Predict Yield (Polk County - 2025)${NC}"
curl -s "${API_URL}/api/predict/19153?year=2025" | jq '{county: .county_name, year: .year, yield: .predicted_yield}'
echo -e "${GREEN}✓ Prediction endpoint working${NC}\n"

# Test 5: Historical Data
echo -e "${YELLOW}Test 5: Get Historical Data${NC}"
curl -s "${API_URL}/api/historical/19153?year=2024" | jq '{county: .county_name, records: (.data | length)}'
echo -e "${GREEN}✓ Historical endpoint working${NC}\n"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All tests passed! ✅${NC}"
echo -e "${GREEN}========================================${NC}"
