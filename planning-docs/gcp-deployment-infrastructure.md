# Google Cloud Platform Deployment Infrastructure Plan

## Overview
Set up cost-effective GCP infrastructure for staging and production deployments, leveraging free tier and on-demand pricing.

## GCP Services to Use

### 1. Compute Engine (VMs)
**Free Tier Benefits:**
- 1 e2-micro instance (0.25 vCPU, 1GB RAM) free per month
- 30GB standard persistent disk
- 1GB network egress

**Cost-Optimized Approach:**
- Use e2-micro for staging (free)
- Use e2-small or spot instances for production
- Stop instances when not in use

### 2. Cloud Storage (Already Using)
- Existing bucket for audio files
- Add deployment artifacts if needed

### 3. Container Registry / Artifact Registry
- Store Docker images
- Integrated with GitHub Actions
- Pay per GB stored (~$0.10/GB/month)

## Deployment Architecture

### Option 1: Single VM with Docker (Recommended for Start)
```
┌─────────────────────────────┐
│   e2-micro (Free Tier)      │
│   ┌──────────┐ ┌─────────┐ │
│   │ Staging  │ │  Prod   │ │
│   │ Port:8081│ │Port:8080│ │
│   └──────────┘ └─────────┘ │
│   Docker + Docker Compose   │
└─────────────────────────────┘
```

### Option 2: Separate VMs (Future Growth)
```
┌───────────────┐    ┌──────────────────┐
│ Staging VM    │    │ Production VM    │
│ e2-micro free │    │ e2-small/spot    │
└───────────────┘    └──────────────────┘
```

## Implementation Plan

### Phase 1: GCP Project Setup
1. **Ensure GCP Project is Ready**
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Enable Required APIs**
   ```bash
   gcloud services enable compute.googleapis.com
   gcloud services enable containerregistry.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   ```

3. **Create Service Account for GitHub Actions**
   ```bash
   gcloud iam service-accounts create github-actions \
     --display-name="GitHub Actions Deployer"
   
   # Grant necessary permissions
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/compute.instanceAdmin"
   
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/storage.admin"
   
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/iam.serviceAccountUser"
   ```

### Phase 2: Compute Engine Setup

#### Create Staging Instance (Free Tier)
```bash
# Create e2-micro instance (free tier)
gcloud compute instances create audio-extract-staging \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-standard \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=http-server,https-server \
  --metadata-from-file startup-script=startup-script.sh
```

#### Firewall Rules
```bash
# Allow HTTP/HTTPS traffic
gcloud compute firewall-rules create allow-audio-extract \
  --allow tcp:8080,tcp:8081 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server
```

### Phase 3: Instance Configuration

#### Startup Script (startup-script.sh)
```bash
#!/bin/bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create deployment directory
sudo mkdir -p /opt/audio-extract
sudo chown $USER:$USER /opt/audio-extract

# Install Google Cloud SDK (for GCS access)
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
sudo apt-get update && sudo apt-get install google-cloud-sdk

# Setup automatic Docker startup
sudo systemctl enable docker
```

### Phase 4: GitHub Secrets Configuration

Create these secrets in GitHub:
```yaml
# For Google Cloud deployment
GCP_PROJECT_ID: your-project-id
GCP_SA_KEY: (base64 encoded service account JSON)
GCP_ZONE: us-central1-a

# For staging
STAGING_HOST: (external IP of staging instance)
STAGING_USER: ubuntu
STAGING_SSH_KEY: (private SSH key for instance)
STAGING_URL: http://EXTERNAL_IP:8081

# For production
PRODUCTION_HOST: (external IP or same as staging)
PRODUCTION_USER: ubuntu
PRODUCTION_SSH_KEY: (private SSH key)
PRODUCTION_URL: http://EXTERNAL_IP:8080

# Existing secrets
GCS_BUCKET_NAME: your-bucket-name
AUDIO_EXTRACT_FOLDER_ID: your-folder-id
```

### Phase 5: Modified GitHub Actions Workflow

Update deployment to use GCP:
```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    credentials_json: ${{ secrets.GCP_SA_KEY }}

- name: Set up Cloud SDK
  uses: google-github-actions/setup-gcloud@v2

- name: Configure Docker for GCR
  run: |
    gcloud auth configure-docker

- name: Push to Google Container Registry
  run: |
    docker tag $IMAGE gcr.io/${{ secrets.GCP_PROJECT_ID }}/$IMAGE_NAME:$TAG
    docker push gcr.io/${{ secrets.GCP_PROJECT_ID }}/$IMAGE_NAME:$TAG
```

## Cost Analysis

### Minimal Setup (Using Free Tier)
- **Compute (e2-micro)**: $0 (free tier)
- **Storage (30GB disk)**: $0 (included)
- **Network**: $0 (1GB free egress)
- **Container Registry**: ~$0.50/month
- **Total**: ~$0.50/month

### Production Setup
- **Staging (e2-micro)**: $0 (free tier)
- **Production (e2-small)**: ~$13/month (or $4/month with spot)
- **Storage**: ~$2/month
- **Network**: ~$1-5/month (depends on traffic)
- **Total**: ~$16-20/month (or ~$7/month with spot)

### On-Demand Strategies
1. **Schedule instances** to run only during business hours
2. **Use Spot VMs** for 60-90% discount
3. **Stop instances** when not in use (pay only for disk)

## Migration from Current SSH-based Deployment

### Option 1: Keep SSH Deployment (Easiest)
- Use existing workflow
- Just update secrets with GCP instance details
- No code changes required

### Option 2: Use GCP-Native Deployment
- Push images to GCR
- Use gcloud commands for deployment
- More "cloud-native" but requires workflow updates

## Next Steps

1. **Week 1 - Setup**
   - Create GCP service account
   - Launch e2-micro instance
   - Configure SSH access
   - Test manual deployment

2. **Week 1 - GitHub Integration**
   - Add GCP secrets to GitHub
   - Test staging deployment
   - Verify health checks

3. **Week 2 - Production**
   - Decide on production instance type
   - Set up monitoring
   - Configure backups

4. **Week 2 - Optimization**
   - Set up instance schedules
   - Configure spot instances
   - Implement cost alerts

## Commands Cheat Sheet

```bash
# Start instance
gcloud compute instances start audio-extract-staging --zone=us-central1-a

# Stop instance (save money)
gcloud compute instances stop audio-extract-staging --zone=us-central1-a

# SSH into instance
gcloud compute ssh audio-extract-staging --zone=us-central1-a

# Check instance status
gcloud compute instances list

# View logs
gcloud compute instances get-serial-port-output audio-extract-staging --zone=us-central1-a
```

## Cost-Saving Tips

1. **Use Committed Use Discounts** (1 or 3 years) for 37-57% off
2. **Schedule instances** to auto-stop at night
3. **Use Spot VMs** for non-critical workloads
4. **Monitor with Budget Alerts** to avoid surprises
5. **Use Cloud Run** instead for true serverless (requires app changes)