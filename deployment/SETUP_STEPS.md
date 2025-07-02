# GCP Setup - Step by Step Guide

## Prerequisites
- Google Cloud SDK installed locally
- Access to the GCP project: `fluted-citizen-269819`

## Step 1: Initial Setup
```bash
# Set your project
gcloud config set project fluted-citizen-269819

# Enable required APIs (this may take a minute)
gcloud services enable compute.googleapis.com containerregistry.googleapis.com
```

## Step 2: Create Firewall Rules
```bash
gcloud compute firewall-rules create allow-audio-extract \
    --allow tcp:80,tcp:443,tcp:8080,tcp:8081 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server \
    --description "Allow HTTP/HTTPS and audio-extract ports"
```

## Step 3: Create the Instance
**IMPORTANT**: Make sure you're in the `deployment` directory and `startup-script.sh` is present!

```bash
cd deployment  # Must be in this directory!

gcloud compute instances create audio-extract-staging \
    --zone=us-central1-a \
    --machine-type=e2-micro \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-standard \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags=http-server \
    --metadata-from-file startup-script=startup-script.sh \
    --scopes=https://www.googleapis.com/auth/cloud-platform
```

## Step 4: Generate SSH Keys
```bash
# Generate a new SSH key for GitHub Actions
ssh-keygen -t ed25519 -f github-actions-key -N "" -C "github-actions"
```

## Step 5: Get Instance IP and Configure SSH
```bash
# Get the external IP
EXTERNAL_IP=$(gcloud compute instances describe audio-extract-staging \
    --zone=us-central1-a \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "Your instance IP is: $EXTERNAL_IP"

# Add the SSH key to the instance
gcloud compute instances add-metadata audio-extract-staging \
    --zone=us-central1-a \
    --metadata-from-file ssh-keys=<(echo "ubuntu:$(cat github-actions-key.pub)")
```

## Step 6: Create Service Account
```bash
# Create service account
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Deployer"

# Set the service account email variable
SERVICE_ACCOUNT="github-actions@fluted-citizen-269819.iam.gserviceaccount.com"

# Grant necessary permissions
gcloud projects add-iam-policy-binding fluted-citizen-269819 \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/compute.instanceAdmin.v1"

gcloud projects add-iam-policy-binding fluted-citizen-269819 \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding fluted-citizen-269819 \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/iam.serviceAccountUser"

# Create service account key
gcloud iam service-accounts keys create github-actions-sa-key.json \
    --iam-account="${SERVICE_ACCOUNT}"
```

## Step 7: Prepare GitHub Secrets

After completing all steps above, run these commands to display your secrets:

```bash
echo "=== GITHUB SECRETS ==="
echo "STAGING_HOST: $EXTERNAL_IP"
echo "STAGING_USER: ubuntu"
echo "STAGING_URL: http://$EXTERNAL_IP:8081"
echo ""
echo "STAGING_SSH_KEY:"
cat github-actions-key
echo ""
echo "GCP_PROJECT_ID: fluted-citizen-269819"
echo "GCP_ZONE: us-central1-a"
echo ""
echo "GCP_SA_KEY (copy the entire output):"
base64 -w 0 github-actions-sa-key.json
```

## Step 8: Add Secrets to GitHub

1. Go to: https://github.com/topherhooper/dnd_notetaker/settings/secrets/actions
2. Click "New repository secret" for each secret
3. Add all the secrets shown above

## Step 9: Verify Instance is Ready

Wait 2-3 minutes for the startup script to complete, then:

```bash
# Check if the instance is responding
curl http://$EXTERNAL_IP:8081/health

# Or SSH into the instance to check
gcloud compute ssh ubuntu@audio-extract-staging --zone=us-central1-a
```

## Useful Commands

```bash
# Stop instance (save money when not using)
gcloud compute instances stop audio-extract-staging --zone=us-central1-a

# Start instance again
gcloud compute instances start audio-extract-staging --zone=us-central1-a

# Check instance status
gcloud compute instances list

# View startup script logs
gcloud compute instances get-serial-port-output audio-extract-staging --zone=us-central1-a
```

## Troubleshooting

If the health check fails:
1. Wait another minute (startup script might still be running)
2. Check the serial console output for errors
3. SSH in and check Docker: `sudo docker ps`

## Next Steps

Once everything is working:
1. Push to a PR to test the deployment workflow
2. The PR should automatically deploy to staging
3. Check the PR comments for the deployment URL