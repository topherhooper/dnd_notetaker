# Deployment Setup Guide

This directory contains scripts to set up Google Cloud Platform infrastructure for deploying the audio-extract service.

## Quick Start

1. **Prerequisites**
   - Google Cloud SDK installed (`gcloud`)
   - GitHub CLI installed (`gh`) - optional but recommended
   - A GCP project with billing enabled

2. **Run the setup script**
   ```bash
   cd deployment
   ./setup-gcp-instance.sh
   ```
   This will:
   - Create an e2-micro instance (free tier eligible)
   - Set up firewall rules
   - Generate SSH keys
   - Create a service account
   - Output GitHub secrets to configure

3. **Configure GitHub secrets**
   
   Option A: Using GitHub CLI (automated)
   ```bash
   ./configure-github-secrets.sh
   ```
   
   Option B: Manual configuration
   - Go to your repository settings → Secrets and variables → Actions
   - Add the secrets shown by the setup script

4. **Verify deployment**
   
   Wait 2-3 minutes for the startup script to complete, then:
   ```bash
   # Check if the instance is ready
   curl http://YOUR_EXTERNAL_IP:8081/health
   ```

## Scripts

### `setup-gcp-instance.sh`
Main setup script that creates the GCP infrastructure:
- Creates e2-micro Compute Engine instance (free tier)
- Sets up networking and firewall rules
- Generates SSH keys for GitHub Actions
- Creates service account with necessary permissions
- Outputs all required GitHub secrets

### `startup-script.sh`
Runs automatically when the instance starts:
- Installs Docker and Docker Compose
- Sets up nginx as reverse proxy
- Clones the repository
- Configures the deployment environment

### `configure-github-secrets.sh`
Helper script to configure GitHub secrets using the GitHub CLI.

## Instance Management

After setup, you can manage your instance with:

```bash
# SSH into the instance
gcloud compute ssh ubuntu@audio-extract-staging --zone=us-central1-a

# Stop instance (save money when not in use)
gcloud compute instances stop audio-extract-staging --zone=us-central1-a

# Start instance
gcloud compute instances start audio-extract-staging --zone=us-central1-a

# View instance status
gcloud compute instances list

# Delete instance (when no longer needed)
gcloud compute instances delete audio-extract-staging --zone=us-central1-a
```

## Cost Management

- **e2-micro instance**: Free (1 per month included in free tier)
- **30GB disk**: Free (included with instance)
- **Network**: 1GB egress free per month

To minimize costs:
- Stop the instance when not in use
- Use the free tier e2-micro for staging
- Consider spot instances for production (60-90% cheaper)

## Troubleshooting

### Instance not responding
1. Check if startup script completed:
   ```bash
   gcloud compute instances get-serial-port-output audio-extract-staging --zone=us-central1-a
   ```

2. SSH in and check Docker:
   ```bash
   gcloud compute ssh ubuntu@audio-extract-staging --zone=us-central1-a
   sudo docker ps
   sudo docker-compose -f /opt/audio-extract/docker-compose.staging.yml logs
   ```

### GitHub Actions deployment failing
1. Verify secrets are set correctly
2. Check instance is running
3. Test SSH connection manually:
   ```bash
   ssh -i github-actions-key ubuntu@EXTERNAL_IP
   ```

### Health check failing
1. Check nginx is running:
   ```bash
   sudo systemctl status nginx
   ```
2. Check Docker containers:
   ```bash
   sudo docker ps
   ```