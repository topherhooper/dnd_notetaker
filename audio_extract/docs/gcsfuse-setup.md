# GCSfuse Setup Guide

This guide explains how to set up GCSfuse for the audio_extract service, enabling transparent cloud storage for extracted audio files.

## Overview

GCSfuse allows the audio_extract service to write files to what appears to be a local filesystem, but the files are actually stored in Google Cloud Storage. This provides:

- Simple development experience (same as local files)
- Automatic cloud backup
- No code changes between environments
- Cost-effective storage

## Prerequisites

1. Google Cloud Project with billing enabled
2. Service account with Storage Admin permissions
3. Docker with privileged mode support
4. GCS bucket created

## Setup Steps

### 1. Create GCS Bucket

```bash
# Create bucket
gsutil mb -p YOUR_PROJECT_ID gs://your-audio-extracts

# Create environment directories
gsutil mkdir gs://your-audio-extracts/dev
gsutil mkdir gs://your-audio-extracts/staging
gsutil mkdir gs://your-audio-extracts/prod
```

### 2. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create audio-extract-gcs \
  --display-name="Audio Extract GCS Access"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:audio-extract-gcs@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Download key
gcloud iam service-accounts keys create gcs-credentials.json \
  --iam-account=audio-extract-gcs@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 3. Local Development

#### Option A: Docker with GCSfuse

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your values
# Set ENABLE_GCSFUSE=true
# Set GCS_BUCKET_NAME=your-audio-extracts

# Start with GCSfuse enabled
docker-compose up
```

#### Option B: Direct GCSfuse Mount (No Docker)

```bash
# Install gcsfuse
# Ubuntu/Debian:
export GCSFUSE_REPO=gcsfuse-`lsb_release -c -s`
echo "deb https://packages.cloud.google.com/apt $GCSFUSE_REPO main" | sudo tee /etc/apt/sources.list.d/gcsfuse.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update && sudo apt-get install gcsfuse

# macOS:
brew install --cask macfuse
brew install gcsfuse

# Mount bucket
mkdir -p ~/audio-extracts-mount
gcsfuse --key-file=gcs-credentials.json --implicit-dirs your-audio-extracts ~/audio-extracts-mount

# Update config to use mount
# In audio_extract_config.dev.yaml:
# storage:
#   local:
#     path: ~/audio-extracts-mount/dev
```

### 4. Production Deployment

```bash
# On production server
cd /opt/audio-extract

# Place credentials
sudo mkdir -p /etc/audio-extract
sudo cp gcs-credentials.json /etc/audio-extract/
sudo chmod 600 /etc/audio-extract/gcs-credentials.json

# Set environment variables
cat >> .env << EOF
ENABLE_GCSFUSE=true
GCS_BUCKET_NAME=your-audio-extracts
GCS_CREDENTIALS_PATH=/etc/audio-extract/gcs-credentials.json
ENVIRONMENT=production
EOF

# Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Verify mount
docker exec audio-extract-prod ls -la /mnt/audio-extracts/prod
```

## Verification

### Check Mount Status
```bash
# In container
docker exec audio-extract-prod mount | grep gcsfuse

# Check health endpoint
curl http://localhost:8081/health | jq .components.storage
```

### Test Write Access
```bash
# In container
docker exec audio-extract-prod touch /mnt/audio-extracts/prod/test.txt

# Verify in GCS
gsutil ls gs://your-audio-extracts/prod/test.txt
```

## Troubleshooting

### Mount Failed
1. Check credentials file exists and is readable
2. Verify service account has Storage Admin role
3. Check container has privileged mode enabled
4. Review logs: `docker logs audio-extract-prod`

### Permission Denied
1. Ensure FUSE device is available: `ls -la /dev/fuse`
2. Check container is running with `--privileged`
3. Verify user has access to mount point

### Files Not Appearing in GCS
1. Check mount options include `--implicit-dirs`
2. Verify bucket name is correct
3. Check network connectivity to GCS
4. Enable debug mode: `GCSFUSE_DEBUG=true`

## Performance Tuning

### Development
```yaml
mount_options: "--implicit-dirs --dir-mode=755 --file-mode=644"
```

### Production
```yaml
mount_options: "--implicit-dirs --dir-mode=755 --file-mode=644 --stat-cache-ttl=10m --type-cache-ttl=10m"
```

### High Volume
```yaml
mount_options: "--implicit-dirs --dir-mode=755 --file-mode=644 --stat-cache-ttl=30m --type-cache-ttl=30m --stat-cache-capacity=100000"
```

## Cost Optimization

1. **Lifecycle Policies**: Archive old files
   ```bash
   gsutil lifecycle set lifecycle.json gs://your-audio-extracts
   ```

2. **Regional Buckets**: Use same region as compute
3. **Monitoring**: Set up budget alerts
4. **Cleanup**: Remove old files periodically

## Security Best Practices

1. **Least Privilege**: Only grant necessary permissions
2. **Separate Accounts**: Use different service accounts for Drive and GCS
3. **Key Rotation**: Rotate service account keys regularly
4. **Audit Logging**: Enable Cloud Audit Logs
5. **VPC Service Controls**: Restrict access to specific networks

## Integration with Dashboard

The audio_extract dashboard automatically displays GCS URLs when files are stored via GCSfuse:

1. Files appear as local paths in the application
2. Dashboard reads the storage path from metadata
3. If bucket is public, direct URLs are shown
4. If private, signed URLs are generated

No additional configuration needed - it just works!