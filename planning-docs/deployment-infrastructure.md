# Deployment Infrastructure Plan

## Overview
Set up minimal-cost infrastructure for staging and production deployments of the audio-extract service. Focus on on-demand costs only, no fixed monthly fees.

## Option 1: Single VPS Approach (Recommended for Budget)
**Cost: ~$6-20/month when running**

### Provider Options:
1. **DigitalOcean Droplet** ($6/month for 1GB RAM)
2. **Linode** ($5/month for 1GB RAM)
3. **Vultr** ($6/month for 1GB RAM)
4. **Hetzner Cloud** ($4.50/month for 2GB RAM - best value)

### Setup:
- Single VPS runs both staging and production (port-separated)
- Staging on port 8081, production on port 8080
- Use Docker Compose with different project names
- Can be turned off when not in use to save costs

## Option 2: Serverless Container Approach
**Cost: Pay only when processing**

### Google Cloud Run
- **Pros:** True pay-per-use, scales to zero
- **Cons:** Requires modifying app for stateless operation
- **Cost:** ~$0.00002400/vCPU-second

### AWS Fargate Spot
- **Pros:** 70% cheaper than regular Fargate
- **Cons:** Can be interrupted, complex setup
- **Cost:** ~$0.01/vCPU/hour when running

## Option 3: Free Tier Options
**Cost: $0 (with limitations)**

### Oracle Cloud Free Tier
- 2 AMD VMs (1/8 OCPU, 1GB RAM each)
- Always free, no expiration
- Can run staging permanently free

### Google Cloud Free Tier
- e2-micro instance (1 vCPU, 1GB RAM)
- Free for 720 hours/month
- Perfect for staging

## Recommended Implementation Plan

### Phase 1: Staging Environment (Week 1)
1. **Set up Hetzner Cloud VPS** ($4.50/month)
   - 2GB RAM, 1 vCPU, 20GB SSD
   - Ubuntu 22.04 LTS
   - Can handle both staging and light production

2. **Configure Server**
   ```bash
   # Install Docker and Docker Compose
   # Set up SSH keys
   # Configure firewall (ufw)
   # Install nginx for reverse proxy
   ```

3. **Set up GitHub Secrets**
   - Generate SSH key pair
   - Add server IP as STAGING_HOST
   - Add 'deploy' user as STAGING_USER
   - Add private key as STAGING_SSH_KEY

### Phase 2: Storage Solution (Week 1)
Since the app uses Google Cloud Storage:

1. **Google Cloud Storage Setup**
   - Create GCS bucket (pay per GB stored)
   - Storage: $0.020/GB/month
   - Operations: $0.005 per 10,000 operations
   - Create service account for authentication

2. **Alternative: Local Storage**
   - Use server's local disk initially
   - Move to GCS when needed
   - Modify code to support both options

### Phase 3: Production Environment (Week 2)
1. **Same VPS Strategy**
   - Run production on same server (different port)
   - Use nginx to route domains
   - Separate Docker Compose projects

2. **Domain Setup (Optional)**
   - Use Cloudflare (free tier)
   - Point staging.yourdomain.com → VPS:8081
   - Point api.yourdomain.com → VPS:8080

### Phase 4: Monitoring & Backups (Week 2)
1. **Monitoring**
   - Use Uptime Kuma (self-hosted, free)
   - Or UptimeRobot (free tier)

2. **Backups**
   - Daily backup script to GCS
   - Or use Hetzner's backup option (+20% cost)

## Cost Breakdown

### Minimal Setup (Recommended)
- **Hetzner VPS**: $4.50/month
- **Storage**: ~$1/month (50GB on GCS)
- **Total**: ~$5.50/month

### On-Demand Only Option
- **Google Cloud Run**: ~$5-10/month (based on usage)
- **Storage**: ~$1/month
- **Total**: $6-11/month (varies with usage)

### Free Tier Option
- **Oracle Cloud VM**: $0
- **Storage**: ~$1/month (GCS)
- **Total**: ~$1/month

## Implementation Steps

### 1. Server Setup Script
Create a script to automate server setup:
```bash
#!/bin/bash
# setup-server.sh
# - Install Docker
# - Create deploy user
# - Set up SSH keys
# - Configure firewall
# - Install nginx
```

### 2. GitHub Actions Secrets
Need to create:
- STAGING_HOST
- STAGING_USER
- STAGING_SSH_KEY
- STAGING_URL
- GCS_SERVICE_ACCOUNT_KEY (base64 encoded)

### 3. Docker Compose Updates
- Ensure docker-compose files use environment variables
- Set up proper volume mounts
- Configure health checks

### 4. Deployment Testing
- Test staging deployment first
- Verify health checks work
- Test PR deployments
- Then set up production

## Decision Points

1. **VPS vs Serverless?**
   - VPS: Simpler, predictable costs
   - Serverless: True on-demand, requires app changes

2. **Single vs Multiple Servers?**
   - Single: Cheaper, adequate for most needs
   - Multiple: Better isolation, more expensive

3. **Storage Solution?**
   - Start with local disk
   - Move to GCS when needed
   - Consider S3-compatible alternatives (Backblaze B2)

## Next Steps

1. Choose hosting provider (recommend Hetzner)
2. Set up server with provided script
3. Configure GitHub secrets
4. Test staging deployment
5. Plan production rollout

This plan prioritizes:
- Minimal fixed costs
- Easy scaling down/pausing
- Simple implementation
- Room for growth