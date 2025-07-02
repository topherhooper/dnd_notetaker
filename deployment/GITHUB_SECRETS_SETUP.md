# GitHub Secrets Setup Instructions

## Overview
These instructions guide you through adding the required secrets to your GitHub repository for automated deployments to the GCP staging environment.

## Prerequisites
- GitHub repository access with admin permissions
- GCP instance already created (completed)
- SSH keys and service account keys generated (completed)

## Required Secrets

### 1. STAGING_HOST
- **Value**: `34.10.10.224`
- **Description**: The external IP address of your GCP staging instance

### 2. STAGING_USER
- **Value**: `ubuntu`
- **Description**: The SSH username for connecting to the staging instance

### 3. STAGING_URL
- **Value**: `http://34.10.10.224:8081`
- **Description**: The URL where the staging application will be accessible

### 4. STAGING_SSH_KEY
- **Value**: The complete private key including BEGIN and END lines
- **Description**: SSH private key for GitHub Actions to connect to the staging instance
- **Important**: Copy the entire key including:
  ```
  -----BEGIN OPENSSH PRIVATE KEY-----
  [key content]
  -----END OPENSSH PRIVATE KEY-----
  ```

### 5. GCP_PROJECT_ID
- **Value**: `fluted-citizen-269819`
- **Description**: Your Google Cloud Project ID

### 6. GCP_ZONE
- **Value**: `us-central1-a`
- **Description**: The GCP zone where your instance is located

### 7. GCP_SA_KEY
- **Value**: Base64 encoded service account JSON key
- **Description**: Service account credentials for GCP operations
- **Important**: This should be the base64 encoded version of the JSON file

## Manual Setup Instructions

1. Navigate to your GitHub repository
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. For each secret listed above:
   - Click **New repository secret**
   - Enter the secret name exactly as shown
   - Paste the corresponding value
   - Click **Add secret**

## Automated Setup Using GitHub CLI

### Prerequisites
- GitHub CLI (`gh`) installed and authenticated
- Terminal access to the directory with the generated keys

### Steps

1. **Ensure you're in the deployment directory**:
   ```bash
   cd /workspaces/dnd_notetaker/deployment
   ```

2. **Set the repository** (if not already set):
   ```bash
   gh repo set-default topherhooper/dnd_notetaker
   ```

3. **Add each secret**:
   ```bash
   # Simple string secrets
   gh secret set STAGING_HOST --body "34.10.10.224"
   gh secret set STAGING_USER --body "ubuntu"
   gh secret set STAGING_URL --body "http://34.10.10.224:8081"
   gh secret set GCP_PROJECT_ID --body "fluted-citizen-269819"
   gh secret set GCP_ZONE --body "us-central1-a"
   
   # File-based secrets
   gh secret set STAGING_SSH_KEY < github-actions-key
   gh secret set GCP_SA_KEY --body "$(base64 -w 0 github-actions-sa-key.json)"
   ```

4. **Verify secrets were added**:
   ```bash
   gh secret list
   ```

## Verification

After adding all secrets, you should see these 7 secrets when running:
```bash
gh secret list
```

Expected output:
```
GCP_PROJECT_ID       Updated 2025-01-02
GCP_SA_KEY          Updated 2025-01-02
GCP_ZONE            Updated 2025-01-02
STAGING_HOST        Updated 2025-01-02
STAGING_SSH_KEY     Updated 2025-01-02
STAGING_URL         Updated 2025-01-02
STAGING_USER        Updated 2025-01-02
```

## Troubleshooting

### GitHub CLI Not Authenticated
If you get authentication errors:
```bash
gh auth login
```

### Repository Not Found
Ensure you're using the correct repository:
```bash
gh repo view
```

### Secret Value Too Large
If you get an error about secret size, ensure you're using the base64 encoded version for GCP_SA_KEY.

## Next Steps

Once all secrets are configured:
1. Wait 2-3 minutes for the instance startup script to complete
2. Test the deployment with: `curl http://34.10.10.224:8081/health`
3. Create a pull request to trigger the automated deployment workflow