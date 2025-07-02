#!/bin/bash
# GCP Infrastructure Setup Script
# Run this after gcloud is properly configured

set -e

# Configuration
PROJECT_ID="fluted-citizen-269819"
ZONE="us-central1-a"
INSTANCE_NAME="audio-extract-staging"

echo "Starting GCP infrastructure setup..."

# 1. Set project
echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# 2. Enable required APIs
echo "Enabling required APIs..."
gcloud services enable compute.googleapis.com containerregistry.googleapis.com

# 3. Create firewall rules
echo "Creating firewall rules..."
gcloud compute firewall-rules create allow-audio-extract \
    --allow tcp:80,tcp:443,tcp:8080,tcp:8081 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server \
    --description "Allow HTTP/HTTPS and audio-extract ports" \
    2>/dev/null || echo "Firewall rule already exists"

# 4. Create instance
echo "Creating compute instance..."
gcloud compute instances create $INSTANCE_NAME \
    --zone=$ZONE \
    --machine-type=e2-micro \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-standard \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags=http-server \
    --metadata-from-file startup-script=startup-script.sh \
    --scopes=https://www.googleapis.com/auth/cloud-platform

# 5. Wait for instance to be ready
echo "Waiting for instance to be ready..."
sleep 30

# 6. Generate SSH key
echo "Generating SSH key for GitHub Actions..."
ssh-keygen -t ed25519 -f github-actions-key -N "" -C "github-actions"

# 7. Get instance IP and add SSH key
echo "Configuring instance..."
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "Instance External IP: $EXTERNAL_IP"

gcloud compute instances add-metadata $INSTANCE_NAME \
    --zone=$ZONE \
    --metadata-from-file ssh-keys=<(echo "ubuntu:$(cat github-actions-key.pub)")

# 8. Create service account
echo "Creating service account..."
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Deployer" \
    2>/dev/null || echo "Service account already exists"

# 9. Grant permissions
SERVICE_ACCOUNT="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"
echo "Granting permissions to service account..."

for role in compute.instanceAdmin.v1 storage.admin iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/${role}"
done

# 10. Create service account key
echo "Creating service account key..."
gcloud iam service-accounts keys create github-actions-sa-key.json \
    --iam-account="${SERVICE_ACCOUNT}"

# Display results
echo ""
echo "========================================="
echo "Setup completed successfully!"
echo "========================================="
echo ""
echo "GitHub Secrets to add:"
echo "STAGING_HOST: $EXTERNAL_IP"
echo "STAGING_USER: ubuntu"
echo "STAGING_URL: http://$EXTERNAL_IP:8081"
echo ""
echo "STAGING_SSH_KEY:"
cat github-actions-key
echo ""
echo "GCP_PROJECT_ID: $PROJECT_ID"
echo "GCP_ZONE: $ZONE"
echo ""
echo "GCP_SA_KEY (base64):"
base64 -w 0 github-actions-sa-key.json
echo ""
echo "========================================="
echo ""
echo "Files created:"
echo "- github-actions-key (SSH private key)"
echo "- github-actions-key.pub (SSH public key)"
echo "- github-actions-sa-key.json (Service account key)"
echo ""
echo "Next steps:"
echo "1. Add the secrets above to your GitHub repository"
echo "2. Wait 2-3 minutes for startup script to complete"
echo "3. Test with: curl http://$EXTERNAL_IP:8081/health"