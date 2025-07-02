#!/bin/bash
# Script to set up GCP Compute Engine instance for audio-extract deployment

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
ZONE="${GCP_ZONE:-us-central1-a}"
INSTANCE_NAME="${INSTANCE_NAME:-audio-extract-staging}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-micro}"  # Free tier eligible

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== GCP Audio Extract Instance Setup ===${NC}"

# Check if project ID is set
if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}Enter your GCP Project ID:${NC}"
    read -r PROJECT_ID
fi

echo -e "${GREEN}Using project: $PROJECT_ID${NC}"
echo -e "${GREEN}Zone: $ZONE${NC}"
echo -e "${GREEN}Instance: $INSTANCE_NAME${NC}"

# Set the project
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable compute.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Create firewall rules
echo -e "${YELLOW}Creating firewall rules...${NC}"
gcloud compute firewall-rules create allow-audio-extract \
    --allow tcp:80,tcp:443,tcp:8080,tcp:8081 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server \
    --description "Allow HTTP/HTTPS and audio-extract ports" \
    2>/dev/null || echo "Firewall rule already exists"

# Create the instance
echo -e "${YELLOW}Creating Compute Engine instance...${NC}"
gcloud compute instances create "$INSTANCE_NAME" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-standard \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags=http-server \
    --metadata-from-file startup-script=startup-script.sh \
    --scopes=https://www.googleapis.com/auth/cloud-platform

# Wait for instance to be ready
echo -e "${YELLOW}Waiting for instance to be ready...${NC}"
sleep 30

# Get instance details
EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo -e "${GREEN}Instance created successfully!${NC}"
echo -e "${GREEN}External IP: $EXTERNAL_IP${NC}"

# Generate SSH key for GitHub Actions
echo -e "${YELLOW}Generating SSH key for GitHub Actions...${NC}"
ssh-keygen -t ed25519 -f github-actions-key -N "" -C "github-actions"

# Copy public key to instance
echo -e "${YELLOW}Adding SSH key to instance...${NC}"
gcloud compute instances add-metadata "$INSTANCE_NAME" \
    --zone="$ZONE" \
    --metadata-from-file ssh-keys=<(echo "ubuntu:$(cat github-actions-key.pub)")

# Create service account for GitHub Actions
echo -e "${YELLOW}Creating service account for GitHub Actions...${NC}"
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Deployer" \
    2>/dev/null || echo "Service account already exists"

# Grant necessary permissions
SERVICE_ACCOUNT="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

echo -e "${YELLOW}Granting permissions to service account...${NC}"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/compute.instanceAdmin.v1"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/iam.serviceAccountUser"

# Create service account key
echo -e "${YELLOW}Creating service account key...${NC}"
gcloud iam service-accounts keys create github-actions-sa-key.json \
    --iam-account="${SERVICE_ACCOUNT}"

# Output GitHub secrets
echo -e "${GREEN}=== GitHub Secrets Configuration ===${NC}"
echo -e "${YELLOW}Add these secrets to your GitHub repository:${NC}"
echo ""
echo "STAGING_HOST: $EXTERNAL_IP"
echo "STAGING_USER: ubuntu"
echo "STAGING_URL: http://${EXTERNAL_IP}:8081"
echo ""
echo "STAGING_SSH_KEY:"
echo "$(cat github-actions-key)"
echo ""
echo "GCP_PROJECT_ID: $PROJECT_ID"
echo "GCP_ZONE: $ZONE"
echo ""
echo "GCP_SA_KEY (base64 encoded):"
echo "$(base64 -w 0 github-actions-sa-key.json)"
echo ""

# Save configuration
cat > instance-config.txt <<EOF
Instance Name: $INSTANCE_NAME
External IP: $EXTERNAL_IP
Zone: $ZONE
Project: $PROJECT_ID
Service Account: $SERVICE_ACCOUNT

To SSH into the instance:
gcloud compute ssh ubuntu@$INSTANCE_NAME --zone=$ZONE

To stop the instance (save money):
gcloud compute instances stop $INSTANCE_NAME --zone=$ZONE

To start the instance:
gcloud compute instances start $INSTANCE_NAME --zone=$ZONE

To delete the instance:
gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE
EOF

echo -e "${GREEN}Configuration saved to instance-config.txt${NC}"
echo -e "${GREEN}SSH private key saved as github-actions-key${NC}"
echo -e "${GREEN}Service account key saved as github-actions-sa-key.json${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Add the secrets shown above to your GitHub repository"
echo "2. Wait 2-3 minutes for startup script to complete"
echo "3. Test the deployment with: curl http://${EXTERNAL_IP}:8081/health"