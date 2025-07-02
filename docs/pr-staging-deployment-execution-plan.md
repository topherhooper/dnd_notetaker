# PR Staging Deployment Execution Plan

## Overview
Implement a GitHub Actions workflow that automatically deploys the head commit of a PR to staging environment after each push. This enables continuous testing of PR changes in a live staging environment.

## Current State Analysis
- **Existing Workflows:**
  - ✅ `build-audio-extract.yml`: Builds Docker images on push/PR
  - ✅ `deploy-audio-extract.yml`: Deploys to staging/production
  - ✅ `deploy-staging-pr.yml`: Created for PR-specific deployments
  - ⚠️ Missing: GitHub secrets for deployment (STAGING_HOST, etc.)

## Infrastructure Setup Progress

### Completed Steps
1. **Created deployment scripts** (in `/deployment` directory)
   - `startup-script.sh` - VM initialization with Docker, nginx
   - `setup-gcp-instance.sh` - GCP infrastructure automation
   - `configure-github-secrets.sh` - GitHub secrets helper
   - `validate-setup.sh` - Setup validation script

2. **Installed Google Cloud SDK**
   - Location: `/opt/google-cloud-sdk`
   - Added to PATH: `export PATH="/opt/google-cloud-sdk/bin:$PATH"`

3. **Cleaned up disk space**
   - Removed unused Docker images: `docker system prune -a -f --volumes`
   - Freed: 13.18GB (disk usage: 95% → 50%)

### Next Infrastructure Steps

#### 4. Authenticate with GCP
```bash
export PATH="/opt/google-cloud-sdk/bin:$PATH"
gcloud auth login  # Interactive
# OR
gcloud auth activate-service-account --key-file=key.json  # Service account
```

#### 5. Create GCP Infrastructure
```bash
# Set project
gcloud config set project fluted-citizen-269819

# Enable APIs
gcloud services enable compute.googleapis.com containerregistry.googleapis.com

# Create firewall rules
gcloud compute firewall-rules create allow-audio-extract \
    --allow tcp:80,tcp:443,tcp:8080,tcp:8081 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server

# Create instance (from deployment directory)
cd /workspaces/dnd_notetaker/deployment
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

#### 6. Configure for GitHub Actions
```bash
# Generate SSH key
ssh-keygen -t ed25519 -f github-actions-key -N "" -C "github-actions"

# Get instance IP and add SSH key
EXTERNAL_IP=$(gcloud compute instances describe audio-extract-staging \
    --zone=us-central1-a \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

gcloud compute instances add-metadata audio-extract-staging \
    --zone=us-central1-a \
    --metadata-from-file ssh-keys=<(echo "ubuntu:$(cat github-actions-key.pub)")

# Create service account
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Deployer"

# Grant permissions
SERVICE_ACCOUNT="github-actions@fluted-citizen-269819.iam.gserviceaccount.com"
for role in compute.instanceAdmin.v1 storage.admin iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding fluted-citizen-269819 \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/${role}"
done

# Create service account key
gcloud iam service-accounts keys create github-actions-sa-key.json \
    --iam-account="${SERVICE_ACCOUNT}"
```

#### 7. Add GitHub Secrets
Required secrets:
- `STAGING_HOST`: [External IP]
- `STAGING_USER`: ubuntu
- `STAGING_URL`: http://[External IP]:8081
- `STAGING_SSH_KEY`: [Contents of github-actions-key]
- `GCP_PROJECT_ID`: fluted-citizen-269819
- `GCP_ZONE`: us-central1-a
- `GCP_SA_KEY`: [Base64 encoded SA key]

### Cost Summary
- **e2-micro instance**: $0 (free tier)
- **30GB disk**: $0 (included)
- **Network**: 1GB free egress
- **Total**: ~$0.50/month (Container Registry)

## Original Implementation Plan

### 1. Create New PR Staging Deployment Workflow
**File:** `.github/workflows/deploy-staging-pr.yml`

**Key Features:**
- Trigger on PR synchronize events (new pushes to PR)
- Build and tag Docker image with PR-specific identifier
- Deploy to staging with PR-specific namespace/subdomain
- Provide deployment URL in PR comment
- Cleanup on PR close

**Workflow Structure:**
```yaml
name: Deploy PR to Staging
on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - 'audio_extract/**'
      - '.github/workflows/deploy-staging-pr.yml'
```

### 2. Deployment Strategy

**Image Tagging:**
- Use format: `pr-{pr_number}-{short_sha}`
- Example: `pr-123-abc1234`

**Deployment Isolation:**
- Each PR gets its own deployment namespace
- Prevent conflicts between multiple PR deployments
- Use Docker Compose with PR-specific project name

**Environment Variables:**
- `PR_NUMBER`: GitHub PR number
- `PR_HEAD_SHA`: Latest commit SHA
- `PR_DEPLOYMENT_URL`: Unique URL for PR deployment

### 3. Integration with Existing Workflows

**Modifications to `deploy-audio-extract.yml`:**
- No changes needed - it will continue to handle main branch deployments
- PR deployments are separate and isolated

**Build Process:**
- Reuse build logic from `build-audio-extract.yml`
- Tag images specifically for PR deployments

### 4. Deployment Lifecycle

**On PR Open/Update:**
1. Build Docker image from PR head commit
2. Tag with PR-specific identifier
3. Deploy to staging with isolated namespace
4. Comment on PR with deployment URL
5. Run smoke tests

**On PR Close:**
1. Cleanup PR-specific deployment
2. Remove Docker images
3. Update PR with cleanup confirmation

### 5. Security Considerations
- Limit deployments to PRs from repository contributors
- Use GitHub environments for secret management
- Implement resource limits for PR deployments

### 6. Testing Strategy
1. Create test PR with audio_extract changes
2. Verify automatic deployment on push
3. Test multiple concurrent PR deployments
4. Verify cleanup on PR close

## Implementation Steps

1. **Create PR deployment workflow file**
   - Implement trigger conditions
   - Add build and deployment steps
   - Configure PR commenting

2. **Setup staging environment**
   - Configure PR-specific namespacing
   - Setup routing for PR deployments
   - Implement resource limits

3. **Add cleanup workflow**
   - Trigger on PR close
   - Remove deployments and images
   - Update PR status

4. **Documentation**
   - Update workflow README
   - Add PR deployment guide
   - Document troubleshooting steps

## Success Criteria
- [ ] PR pushes automatically trigger staging deployment
- [ ] Each PR has isolated deployment environment
- [ ] Deployment URL is posted as PR comment
- [ ] Cleanup happens automatically on PR close
- [ ] Multiple PRs can be deployed simultaneously
- [ ] Deployments complete within 5 minutes

## Rollback Plan
If issues arise:
1. Disable workflow via GitHub UI
2. Manually cleanup any stuck deployments
3. Revert workflow changes if needed
4. Document issues for resolution