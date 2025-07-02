#!/bin/bash
# Script to validate GCP setup after instance creation

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== GCP Setup Validation ===${NC}"

# Check if instance exists
echo -e "${YELLOW}Checking instance...${NC}"
if gcloud compute instances describe audio-extract-staging --zone=us-central1-a &>/dev/null; then
    echo -e "${GREEN}✓ Instance exists${NC}"
    
    # Get IP
    EXTERNAL_IP=$(gcloud compute instances describe audio-extract-staging \
        --zone=us-central1-a \
        --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
    echo -e "${GREEN}✓ External IP: $EXTERNAL_IP${NC}"
else
    echo -e "${RED}✗ Instance not found${NC}"
    exit 1
fi

# Check instance status
STATUS=$(gcloud compute instances describe audio-extract-staging \
    --zone=us-central1-a \
    --format='get(status)')
if [ "$STATUS" = "RUNNING" ]; then
    echo -e "${GREEN}✓ Instance is running${NC}"
else
    echo -e "${YELLOW}! Instance status: $STATUS${NC}"
fi

# Check if service account exists
echo -e "${YELLOW}Checking service account...${NC}"
if gcloud iam service-accounts describe github-actions@fluted-citizen-269819.iam.gserviceaccount.com &>/dev/null; then
    echo -e "${GREEN}✓ Service account exists${NC}"
else
    echo -e "${RED}✗ Service account not found${NC}"
fi

# Check if SSH key was generated
if [ -f "github-actions-key" ]; then
    echo -e "${GREEN}✓ SSH key found${NC}"
else
    echo -e "${RED}✗ SSH key not found${NC}"
fi

# Check if service account key was generated
if [ -f "github-actions-sa-key.json" ]; then
    echo -e "${GREEN}✓ Service account key found${NC}"
else
    echo -e "${RED}✗ Service account key not found${NC}"
fi

# Test HTTP connectivity (might fail if startup script is still running)
echo -e "${YELLOW}Testing HTTP connectivity...${NC}"
if curl -f -m 5 "http://$EXTERNAL_IP:8081/health" &>/dev/null; then
    echo -e "${GREEN}✓ Health check endpoint responding${NC}"
else
    echo -e "${YELLOW}! Health check not responding yet (startup script might still be running)${NC}"
    echo -e "${YELLOW}  Try again in 2-3 minutes or check logs with:${NC}"
    echo "  gcloud compute instances get-serial-port-output audio-extract-staging --zone=us-central1-a"
fi

# Display next steps
echo ""
echo -e "${GREEN}=== Next Steps ===${NC}"
echo "1. If health check failed, wait 2-3 minutes and run this script again"
echo "2. Add the following secrets to GitHub:"
echo "   - STAGING_HOST: $EXTERNAL_IP"
echo "   - STAGING_USER: ubuntu"
echo "   - STAGING_URL: http://$EXTERNAL_IP:8081"
echo "   - STAGING_SSH_KEY: (contents of github-actions-key)"
echo "   - GCP_PROJECT_ID: fluted-citizen-269819"
echo "   - GCP_ZONE: us-central1-a"
echo "   - GCP_SA_KEY: (base64 encoded github-actions-sa-key.json)"
echo ""
echo "3. To SSH into the instance:"
echo "   gcloud compute ssh ubuntu@audio-extract-staging --zone=us-central1-a"