# Audio Extract Service Deployment Guide

This guide outlines the complete deployment process for the audio extract service, from local development to production deployment using Docker, GitHub Actions, and Google Cloud Storage (GCS) via gcsfuse.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Local Development](#local-development)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Staging Deployment](#staging-deployment)
7. [Production Deployment](#production-deployment)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)
9. [Troubleshooting](#troubleshooting)

## Overview

The audio extract service automatically monitors Google Drive folders for meeting recordings and extracts audio files. The deployment uses:

- **Docker** for containerization
- **GitHub Actions** for CI/CD
- **GCSfuse** for transparent cloud storage
- **Multiple environments** (dev, staging, production)

### Key Features

- Zero-downtime deployments
- Automatic health checks
- Cloud storage integration without code changes
- Environment-specific configurations
- Comprehensive monitoring and alerting

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Google Drive   │────▶│  Audio Extract   │────▶│  Google Cloud   │
│  (Video Files)  │     │    Service       │     │  Storage (GCS)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   Dashboard      │
                        │  (Health/Stats)  │
                        └──────────────────┘
```

### Components

1. **Google Drive Monitor**: Polls Drive folders for new recordings
2. **Audio Extractor**: Uses FFmpeg to extract audio from videos
3. **GCSfuse Mount**: Makes GCS appear as local filesystem
4. **Web Dashboard**: Provides health status and download links
5. **Processing Tracker**: SQLite database tracking processed files

## Prerequisites

### Required Accounts and Access

1. **Google Cloud Platform**
   - Project with billing enabled
   - Storage Admin permissions
   - Service account for GCS access

2. **Google Drive API**
   - Service account with Drive access
   - Access to target Drive folders

3. **GitHub**
   - Repository with Actions enabled
   - Container Registry access (ghcr.io)

4. **Infrastructure**
   - Docker with privileged mode support
   - Linux servers for staging/production
   - SSL certificates for HTTPS

### Required Tools

- Docker & Docker Compose
- Google Cloud SDK (`gcloud`, `gsutil`)
- Git
- Make (optional but recommended)

## Local Development

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/your-org/dnd_notetaker.git
cd dnd_notetaker/audio_extract

# Copy environment template
cp .env.example .env

# Edit .env with your values
nano .env
```

### 2. Configure Credentials

```bash
# Create credentials directory
mkdir -p credentials

# Add service account files
cp /path/to/drive-service-account.json credentials/
cp /path/to/gcs-service-account.json credentials/

# Set permissions
chmod 600 credentials/*.json
```

### 3. Run Locally

#### Without GCS (Local Storage)

```bash
# Start service
docker-compose up

# Access dashboard
open http://localhost:8080
```

#### With GCS (Cloud Storage)

```bash
# Enable GCSfuse in environment
export ENABLE_GCSFUSE=true
export GCS_BUCKET_NAME=your-audio-extracts-dev

# Start service with GCS
docker-compose up
```

### 4. Development Workflow

```bash
# Run tests
make test

# Check code quality
make lint

# Build Docker image
make docker-build

# View logs
docker-compose logs -f
```

## CI/CD Pipeline

### GitHub Actions Workflows

The deployment pipeline consists of four workflows:

1. **Test Workflow** (`tests.yml`)
   - Runs on every push/PR
   - Tests both main code and audio_extract module
   - Multiple Python versions (3.9-3.12)

2. **Build Workflow** (`build-audio-extract.yml`)
   - Triggers on main branch changes
   - Builds multi-platform Docker images
   - Pushes to GitHub Container Registry

3. **Deploy Workflow** (`deploy-audio-extract.yml`)
   - Automatic staging deployment
   - Manual approval for production
   - Health checks and rollback

4. **Release Workflow** (`release-audio-extract.yml`)
   - Creates versioned releases
   - Generates changelogs
   - Publishes artifacts

### Deployment Flow

```
Code Push → Tests Pass → Build Image → Deploy Staging → Manual Approval → Deploy Production
```

## Staging Deployment

### 1. Initial Server Setup

```bash
# On staging server
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy

# Create application directory
sudo mkdir -p /opt/audio-extract
sudo chown deploy:deploy /opt/audio-extract

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker
```

### 2. Configure Secrets

In GitHub repository settings:

```
Settings → Secrets and variables → Actions

Add:
- STAGING_HOST: staging.example.com
- STAGING_USER: deploy
- STAGING_SSH_KEY: (private key content)
- GCS_BUCKET_NAME_STAGING: your-audio-extracts-staging
- AUDIO_EXTRACT_FOLDER_ID_STAGING: (Drive folder ID)
```

### 3. Deploy to Staging

```bash
# Automatic deployment on push to main
git push origin main

# Or manual deployment
gh workflow run deploy-audio-extract.yml \
  -f environment=staging \
  -f image_tag=latest
```

### 4. Verify Staging

```bash
# SSH to staging
ssh deploy@staging.example.com

# Check status
docker ps
docker logs audio-extract-staging

# Test health endpoint
curl http://localhost:8081/health

# Check GCS mount
docker exec audio-extract-staging ls /mnt/audio-extracts/staging
```

## Production Deployment

### 1. Production Server Setup

Similar to staging, but with additional security:

```bash
# Restrict SSH access
sudo ufw allow from YOUR_IP to any port 22
sudo ufw enable

# Configure fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban

# Set up monitoring
sudo apt install prometheus-node-exporter
```

### 2. Configure Production Secrets

```
GitHub Settings → Environments → Production

Protection rules:
- Required reviewers: 1
- Restrict deployments to main branch

Secrets:
- PRODUCTION_HOST: prod.example.com
- PRODUCTION_USER: deploy
- PRODUCTION_SSH_KEY: (different from staging)
- GCS_BUCKET_NAME: your-audio-extracts-prod
- AUDIO_EXTRACT_FOLDER_ID: (production Drive folder)
```

### 3. Deploy to Production

```bash
# Requires manual approval in GitHub UI
# After staging deployment succeeds

# Or manual deployment with specific version
gh workflow run deploy-audio-extract.yml \
  -f environment=production \
  -f image_tag=v1.2.3
```

### 4. Production Verification

```bash
# Health check
curl https://prod.example.com/health

# Monitor logs
ssh deploy@prod.example.com
docker logs -f audio-extract-prod --tail 100

# Check metrics
curl http://localhost:8081/metrics
```

## Monitoring and Maintenance

### 1. Health Monitoring

The service provides three health endpoints:

- `/health` - Overall system health
- `/ready` - Readiness for traffic
- `/live` - Liveness check

Example monitoring setup:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'audio-extract'
    static_configs:
      - targets: ['localhost:8081']
```

### 2. Log Management

```bash
# View logs
docker logs audio-extract-prod

# Follow logs
docker logs -f audio-extract-prod

# Export logs
docker logs audio-extract-prod > audio-extract-$(date +%Y%m%d).log

# Log rotation (automatic in Docker)
# Configured in docker-compose.yml:
# max-size: "10m"
# max-file: "3"
```

### 3. Backup Strategy

```bash
# Backup database
docker exec audio-extract-prod \
  sqlite3 /app/data/processed.db ".backup /app/data/backup.db"

# Backup to GCS
gsutil cp backup.db gs://your-backups/audio-extract/

# Automated backup script
cat > /opt/audio-extract/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d-%H%M%S)
docker exec audio-extract-prod \
  sqlite3 /app/data/processed.db ".backup /tmp/backup-$DATE.db"
gsutil cp /tmp/backup-$DATE.db gs://your-backups/audio-extract/
find /tmp -name "backup-*.db" -mtime +7 -delete
EOF

# Schedule with cron
echo "0 2 * * * /opt/audio-extract/backup.sh" | crontab -
```

### 4. Updates and Maintenance

```bash
# Update to latest version
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# View current version
docker inspect audio-extract-prod | jq '.[0].Config.Labels'

# Rollback to previous version
docker-compose -f docker-compose.prod.yml up -d \
  --scale audio-extract=2
# Wait for health check
docker-compose -f docker-compose.prod.yml up -d \
  --scale audio-extract=1 --remove-orphans
```

## Troubleshooting

### Common Issues

#### 1. GCSfuse Mount Failed

```bash
# Check logs
docker logs audio-extract-prod | grep gcsfuse

# Verify credentials
docker exec audio-extract-prod \
  ls -la /app/credentials/

# Test mount manually
docker exec -it audio-extract-prod bash
gcsfuse --debug_gcs --debug_fuse your-bucket /mnt/test
```

#### 2. Drive API Errors

```bash
# Check service account permissions
docker exec audio-extract-prod \
  python -c "from google.oauth2 import service_account; print('OK')"

# Verify folder access
docker exec audio-extract-prod \
  python -m audio_extract.cli.monitor --test
```

#### 3. High Memory Usage

```bash
# Check container stats
docker stats audio-extract-prod

# Increase memory limit
# Edit docker-compose.prod.yml:
# deploy:
#   resources:
#     limits:
#       memory: 4G

# Restart
docker-compose -f docker-compose.prod.yml up -d
```

#### 4. Dashboard Not Accessible

```bash
# Check if running
curl http://localhost:8080

# Check Nginx proxy
docker logs audio-extract-nginx

# Verify port binding
netstat -tlnp | grep 8080
```

### Debug Mode

```bash
# Enable debug logging
docker-compose -f docker-compose.prod.yml down
GCSFUSE_DEBUG=true docker-compose -f docker-compose.prod.yml up

# Interactive debugging
docker exec -it audio-extract-prod python
>>> from audio_extract import AudioExtractor
>>> extractor = AudioExtractor()
>>> # Test extraction
```

### Recovery Procedures

#### Database Corruption

```bash
# Stop service
docker-compose -f docker-compose.prod.yml down

# Restore from backup
gsutil cp gs://your-backups/audio-extract/latest.db recovered.db
docker cp recovered.db audio-extract-prod:/app/data/processed.db

# Restart
docker-compose -f docker-compose.prod.yml up -d
```

#### Full System Recovery

```bash
# 1. Restore server from snapshot
# 2. Install Docker
curl -fsSL https://get.docker.com | sh

# 3. Clone configuration
git clone https://github.com/your-org/dnd_notetaker.git
cd dnd_notetaker/audio_extract

# 4. Restore credentials
gsutil cp -r gs://your-backups/credentials/ .

# 5. Start service
docker-compose -f docker-compose.prod.yml up -d
```

## Security Best Practices

1. **Credentials Management**
   - Use separate service accounts for Drive and GCS
   - Rotate keys every 90 days
   - Never commit credentials to git

2. **Network Security**
   - Dashboard accessible only from localhost
   - Use reverse proxy with SSL
   - Implement rate limiting

3. **Container Security**
   - Run as non-root user
   - Use read-only mounts where possible
   - Keep base images updated

4. **Monitoring**
   - Set up alerts for failures
   - Monitor resource usage
   - Track API quotas

## Conclusion

This deployment guide provides a complete path from local development to production deployment. The use of Docker, GitHub Actions, and GCSfuse creates a robust, scalable system that's easy to maintain and monitor.

For additional help:
- Check logs: `docker logs audio-extract-prod`
- Review documentation: `/audio_extract/README.md`
- Monitor health: `curl http://localhost:8081/health`