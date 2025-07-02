# PR Staging Deployment Execution Plan

## Overview
Implement a GitHub Actions workflow that automatically deploys the head commit of a PR to staging environment after each push. This enables continuous testing of PR changes in a live staging environment.

## Current State Analysis
- **Existing Workflows:**
  - `build-audio-extract.yml`: Builds Docker images on push/PR
  - `deploy-audio-extract.yml`: Deploys to staging/production (currently only triggers on main/master)
  - Current staging deployment only happens after merge to main/master

## Implementation Plan

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