# GitHub Actions Workflows

This directory contains CI/CD workflows for the dnd_notetaker project.

## Workflows

### 1. tests.yml
- **Trigger**: Push/PR to main/master branches
- **Purpose**: Run tests for the entire repository and audio_extract module
- **Jobs**:
  - `test`: Main repository tests
  - `test-audio-extract`: Audio extraction module specific tests

### 2. build-audio-extract.yml
- **Trigger**: 
  - Push to main/master with changes in audio_extract/
  - Tags matching `audio-extract-v*`
  - Manual workflow dispatch
- **Purpose**: Build and push Docker images to GitHub Container Registry
- **Output**: Multi-platform Docker images (linux/amd64, linux/arm64)

### 3. deploy-audio-extract.yml
- **Trigger**:
  - Successful completion of build workflow
  - Manual workflow dispatch
- **Purpose**: Deploy audio_extract service to staging and production
- **Environments**:
  - `staging`: Automatic deployment after build
  - `production`: Requires manual approval
- **Features**:
  - Zero-downtime rolling deployments
  - Health checks after deployment
  - Automatic rollback on failure

### 4. release-audio-extract.yml
- **Trigger**:
  - Tags matching `audio-extract-v*`
  - Manual workflow dispatch with version input
- **Purpose**: Create releases with changelog and artifacts
- **Outputs**:
  - GitHub Release with changelog
  - Configuration archives
  - Documentation archives
  - Python packages

## Required Secrets

### Container Registry
- `GITHUB_TOKEN`: Automatically provided for ghcr.io access

### Deployment
- `STAGING_HOST`: Staging server hostname
- `STAGING_USER`: SSH user for staging
- `STAGING_SSH_KEY`: SSH private key for staging
- `PRODUCTION_HOST`: Production server hostname
- `PRODUCTION_USER`: SSH user for production
- `PRODUCTION_SSH_KEY`: SSH private key for production

### Application Configuration
- `GCS_BUCKET_NAME`: Google Cloud Storage bucket name
- `AUDIO_EXTRACT_FOLDER_ID`: Google Drive folder ID to monitor
- `GCS_SERVICE_ACCOUNT_KEY`: Base64 encoded GCS service account JSON

### Monitoring
- `STAGING_URL`: Staging environment URL for health checks
- `PRODUCTION_URL`: Production environment URL for health checks
- `SLACK_WEBHOOK`: Slack webhook for deployment notifications
- `CODECOV_TOKEN`: Token for code coverage reporting

## Usage

### Manual Deployment
```yaml
# Deploy specific version to staging
gh workflow run deploy-audio-extract.yml \
  -f environment=staging \
  -f image_tag=v1.2.3

# Deploy to production
gh workflow run deploy-audio-extract.yml \
  -f environment=production \
  -f image_tag=v1.2.3
```

### Create Release
```yaml
# Create a new release
gh workflow run release-audio-extract.yml \
  -f version=1.2.3 \
  -f prerelease=false
```

## Environment Setup

1. **GitHub Environments**: Create `staging` and `production` environments in repository settings
2. **Protection Rules**: Add reviewers for production environment
3. **Secrets**: Add environment-specific secrets
4. **Branch Protection**: Require PR reviews and passing tests before merge