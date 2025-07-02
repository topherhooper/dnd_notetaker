#!/bin/bash
# Script to authenticate and set up GCP infrastructure

set -e
export PATH="/opt/google-cloud-sdk/bin:$PATH"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== GCP Authentication and Setup ===${NC}"
echo ""
echo -e "${YELLOW}You need to authenticate with Google Cloud.${NC}"
echo "Options:"
echo "1. Run 'gcloud auth login' on your local machine and copy credentials"
echo "2. Use a service account key"
echo ""
echo "For option 1 (recommended for personal use):"
echo "  - Run: gcloud auth login"
echo "  - Follow the browser authentication"
echo "  - Then run this script again"
echo ""
echo "For option 2 (if you have a service account key):"
echo "  - Place the key file in this directory"
echo "  - Run: gcloud auth activate-service-account --key-file=YOUR_KEY_FILE.json"
echo ""
echo -e "${YELLOW}Press Enter once you're authenticated...${NC}"
read

# Check if authenticated
if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${GREEN}✓ Authenticated successfully${NC}"
else
    echo -e "${RED}✗ Not authenticated. Please authenticate first.${NC}"
    exit 1
fi

# Now run the setup
cd /workspaces/dnd_notetaker/deployment
bash setup-gcp-instance.sh