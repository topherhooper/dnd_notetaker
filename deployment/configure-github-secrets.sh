#!/bin/bash
# Script to help configure GitHub secrets after GCP setup

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== GitHub Secrets Configuration Helper ===${NC}"

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}GitHub CLI (gh) is not installed.${NC}"
    echo "Install it from: https://cli.github.com/"
    echo "Or manually add the secrets at: https://github.com/topherhooper/dnd_notetaker/settings/secrets/actions"
    exit 1
fi

# Check if we're in the right repo
REPO_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [[ ! "$REPO_URL" =~ "dnd_notetaker" ]]; then
    echo -e "${YELLOW}Warning: Not in dnd_notetaker repository${NC}"
fi

# Check if authenticated
if ! gh auth status &>/dev/null; then
    echo -e "${YELLOW}Authenticating with GitHub...${NC}"
    gh auth login
fi

# Function to set secret
set_secret() {
    local name=$1
    local value=$2
    local env=${3:-""}
    
    if [ -n "$env" ]; then
        echo -e "${YELLOW}Setting secret $name in $env environment...${NC}"
        echo "$value" | gh secret set "$name" --env "$env"
    else
        echo -e "${YELLOW}Setting repository secret $name...${NC}"
        echo "$value" | gh secret set "$name"
    fi
}

# Check if instance-config.txt exists
if [ ! -f "instance-config.txt" ]; then
    echo -e "${RED}instance-config.txt not found. Run setup-gcp-instance.sh first.${NC}"
    exit 1
fi

# Extract values from instance-config.txt
EXTERNAL_IP=$(grep "External IP:" instance-config.txt | cut -d' ' -f3)
PROJECT_ID=$(grep "Project:" instance-config.txt | cut -d' ' -f2)
ZONE=$(grep "Zone:" instance-config.txt | cut -d' ' -f2)

echo -e "${GREEN}Found configuration:${NC}"
echo "External IP: $EXTERNAL_IP"
echo "Project ID: $PROJECT_ID"
echo "Zone: $ZONE"

# Ask about environment
echo -e "${YELLOW}Do you want to set secrets for:${NC}"
echo "1) Repository level (available to all workflows)"
echo "2) Staging environment only"
echo "3) Both repository and staging environment"
read -p "Choice (1-3): " choice

case $choice in
    1) ENV_TARGET="" ;;
    2) ENV_TARGET="staging" ;;
    3) ENV_TARGET="both" ;;
    *) echo "Invalid choice"; exit 1 ;;
esac

# Set the secrets
if [ "$ENV_TARGET" = "both" ]; then
    # Set repository level
    set_secret "STAGING_HOST" "$EXTERNAL_IP"
    set_secret "STAGING_USER" "ubuntu"
    set_secret "STAGING_URL" "http://${EXTERNAL_IP}:8081"
    set_secret "STAGING_SSH_KEY" "$(cat github-actions-key)"
    set_secret "GCP_PROJECT_ID" "$PROJECT_ID"
    set_secret "GCP_ZONE" "$ZONE"
    set_secret "GCP_SA_KEY" "$(base64 -w 0 github-actions-sa-key.json)"
    
    # Also set in staging environment
    set_secret "STAGING_HOST" "$EXTERNAL_IP" "staging"
    set_secret "STAGING_USER" "ubuntu" "staging"
    set_secret "STAGING_URL" "http://${EXTERNAL_IP}:8081" "staging"
    set_secret "STAGING_SSH_KEY" "$(cat github-actions-key)" "staging"
else
    set_secret "STAGING_HOST" "$EXTERNAL_IP" "$ENV_TARGET"
    set_secret "STAGING_USER" "ubuntu" "$ENV_TARGET"
    set_secret "STAGING_URL" "http://${EXTERNAL_IP}:8081" "$ENV_TARGET"
    set_secret "STAGING_SSH_KEY" "$(cat github-actions-key)" "$ENV_TARGET"
    set_secret "GCP_PROJECT_ID" "$PROJECT_ID" "$ENV_TARGET"
    set_secret "GCP_ZONE" "$ZONE" "$ENV_TARGET"
    set_secret "GCP_SA_KEY" "$(base64 -w 0 github-actions-sa-key.json)" "$ENV_TARGET"
fi

echo -e "${GREEN}GitHub secrets configured successfully!${NC}"

# Check if we need to create staging environment
if [ "$ENV_TARGET" = "staging" ] || [ "$ENV_TARGET" = "both" ]; then
    echo -e "${YELLOW}Note: Make sure the 'staging' environment exists in your repository.${NC}"
    echo "You can create it at: https://github.com/topherhooper/dnd_notetaker/settings/environments"
fi

echo -e "${GREEN}Next steps:${NC}"
echo "1. Verify secrets at: https://github.com/topherhooper/dnd_notetaker/settings/secrets/actions"
echo "2. Test deployment by pushing to a PR or running the workflow manually"
echo "3. Monitor at: http://${EXTERNAL_IP}:8081/health"