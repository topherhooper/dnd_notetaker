# Audio Extract Service - Production Enhancement Plan

**Status: COMPLETED** - All features have been implemented successfully.

## Overview and Motivation

The audio_extract service is a standalone module that monitors Google Drive folders for Google Meet recordings and automatically extracts audio files. While the core functionality is working, this plan focuses on making the service production-ready with cloud storage integration, robust deployment options, and enhanced monitoring capabilities.

### Current State

The audio_extract module currently has:
- **Working Features**:
  - Google Drive folder monitoring with service account authentication
  - FFmpeg-based audio extraction (MP3, 128k bitrate)
  - SQLite-based tracking to avoid reprocessing
  - Config-driven behavior (dev/prod modes)
  - Web dashboard for development monitoring
  - Comprehensive test suite
  - "Fail fast" error philosophy for debugging

- **Storage**: Local file system for audio files, SQLite for metadata
- **Deployment**: Manual Python execution
- **Monitoring**: Basic web dashboard (dev only)

### Target State

Transform audio_extract into a production-ready service with:
- **Google Cloud Storage (GCS)** for audio file storage
- **Enhanced tracking** with PostgreSQL option
- **Robust deployment** via Docker and systemd
- **Production monitoring** with metrics and alerts
- **Improved reliability** with retries and error recovery
- **Performance optimization** for large-scale processing

## Architecture Design

### 1. Current Module Structure

```
audio_extract/
├── __init__.py            # Module exports
├── extractor.py           # FFmpeg audio extraction
├── chunker.py             # Audio file chunking
├── tracker.py             # SQLite processing tracker
├── utils.py               # Utilities
├── exceptions.py          # Custom exceptions
├── config.py              # Configuration management
├── drive/                 # Google Drive integration
│   ├── client.py          # Drive API client
│   ├── monitor.py         # Monitoring service
│   └── auth.py            # Authentication
├── cli/                   # CLI tools
│   └── monitor.py         # Monitor command
├── dashboard/             # Web dashboard
└── tests/                 # Test suite
```

### 2. Processing Flow

```
Google Drive Folder
        ↓ Monitor
   New Recording Found
        ↓ Download
   Temp Video File
        ↓ Extract
   Audio File (MP3)
        ↓ Upload
   Google Cloud Storage
        ↓ Track
   Processing Database
```

## Google Cloud Storage Integration

### 1. Storage Architecture

```yaml
# GCS Bucket Structure
audio-extracts/
├── 2025/
│   ├── 01/
│   │   ├── meeting_2025-01-29_10-00_audio.mp3
│   │   └── meeting_2025-01-29_14-30_audio.mp3
│   └── 02/
│       └── standup_2025-02-01_09-00_audio.mp3
└── metadata/
    └── processing-logs/
```

### 2. Implementation Plan

#### Phase 1: GCS Client Integration
```python
# audio_extract/storage/gcs_client.py
class GCSStorage:
    def __init__(self, bucket_name: str, credentials_path: str):
        self.client = storage.Client.from_service_account_json(credentials_path)
        self.bucket = self.client.bucket(bucket_name)
    
    def upload_audio(self, local_path: Path, gcs_path: str) -> str:
        """Upload audio file to GCS and return public URL."""
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_filename(str(local_path))
        return blob.public_url
    
    def generate_signed_url(self, gcs_path: str, expiration_hours: int = 24) -> str:
        """Generate temporary signed URL for private access."""
        blob = self.bucket.blob(gcs_path)
        return blob.generate_signed_url(timedelta(hours=expiration_hours))
```

#### Phase 2: Simplified Configuration with gcsfuse

With gcsfuse, both dev and prod can use the same simple file-based approach:

```yaml
# audio_extract_config.dev.yaml
processing:
  # With gcsfuse mount, this writes directly to GCS
  output_directory: /output/dev  # Maps to ~/audio-extracts-mount/dev
  # or for local testing without gcsfuse:
  # output_directory: ./output/dev

# audio_extract_config.prod.yaml  
processing:
  # In production, can either:
  # 1. Use gcsfuse mount (simple, same as dev)
  output_directory: /mnt/audio-extracts/prod
  # 2. Or implement direct GCS API uploads (more control)
  use_gcs_api: true
  gcs:
    bucket_name: my-audio-extracts
    prefix: prod/
    credentials_path: /etc/audio-extract/gcs-credentials.json
```

This approach means:
- Development uses gcsfuse for transparent GCS access
- Production can use either gcsfuse or direct API
- No code changes needed between environments
- Fallback to local storage always available

#### Phase 3: Tracker Enhancement
```sql
-- Add GCS metadata to tracking database
ALTER TABLE processed_videos ADD COLUMN gcs_url TEXT;
ALTER TABLE processed_videos ADD COLUMN gcs_path TEXT;
ALTER TABLE processed_videos ADD COLUMN upload_timestamp TIMESTAMP;
```

### 3. Development Approach with gcsfuse

For development, we can use gcsfuse to mount the GCS bucket as a local filesystem, eliminating the need for code changes between dev and prod:

#### Install gcsfuse
```bash
# Ubuntu/Debian
export GCSFUSE_REPO=gcsfuse-`lsb_release -c -s`
echo "deb https://packages.cloud.google.com/apt $GCSFUSE_REPO main" | sudo tee /etc/apt/sources.list.d/gcsfuse.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update && sudo apt-get install gcsfuse

# macOS
brew install --cask macfuse
brew install gcsfuse
```

#### Mount GCS Bucket
```bash
# Create mount point
mkdir -p ~/audio-extracts-mount

# Mount bucket (with service account)
gcsfuse --key-file=/path/to/service-account.json \
        --implicit-dirs \
        --dir-mode=755 \
        --file-mode=644 \
        my-audio-extracts ~/audio-extracts-mount

# For development config, just point to mount
output_directory: ~/audio-extracts-mount/dev
```

#### Docker Compose with gcsfuse
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  audio-extract:
    build: .
    privileged: true  # Required for FUSE
    cap_add:
      - SYS_ADMIN
    devices:
      - /dev/fuse
    volumes:
      - ./configs:/app/configs
      - type: bind
        source: ${HOME}/audio-extracts-mount
        target: /output
        bind:
          propagation: shared
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/configs/service-account.json
    command: ["--config", "/app/configs/audio_extract_config.dev.yaml"]
```

#### Benefits of gcsfuse for Development
- **Zero Code Changes**: Same code writes to "local" directory that's actually GCS
- **Immediate Visibility**: Files appear in GCS instantly
- **No Upload Logic**: No need for separate upload step
- **Cost Effective**: Only pay for storage, not API calls
- **Simple Testing**: Can browse files with gsutil or GCS console

### 4. Benefits of GCS

- **Scalability**: Unlimited storage capacity
- **Reliability**: 99.999999999% (11 9's) durability
- **Integration**: Native integration with other GCP services
- **Access Control**: Fine-grained permissions and signed URLs
- **Cost Effective**: Lifecycle policies for archival
- **CDN Ready**: Cloud CDN integration for global distribution

## Deployment Strategy

### 1. Docker Containerization

```dockerfile
# Dockerfile
FROM python:3.9-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run as non-root user
RUN useradd -m -u 1000 audioextract
USER audioextract

ENTRYPOINT ["python", "-m", "audio_extract.cli.monitor"]
```

### 2. Docker Compose for Development

```yaml
# docker-compose.yml
version: '3.8'
services:
  audio-extract:
    build: .
    volumes:
      - ./configs:/app/configs
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/configs/service-account.json
    ports:
      - "8080:8080"  # Dashboard
    command: ["--config", "/app/configs/audio_extract_config.dev.yaml"]
```

### 3. Systemd Service

```ini
# /etc/systemd/system/audio-extract.service
[Unit]
Description=Audio Extract Monitor Service
After=network.target

[Service]
Type=simple
User=audioextract
Group=audioextract
WorkingDirectory=/opt/audio-extract
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="GOOGLE_APPLICATION_CREDENTIALS=/etc/audio-extract/credentials.json"
ExecStart=/usr/bin/python3 -m audio_extract.cli.monitor --config /etc/audio-extract/config.prod.yaml
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 4. Kubernetes Deployment (Future)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: audio-extract
spec:
  replicas: 1
  selector:
    matchLabels:
      app: audio-extract
  template:
    metadata:
      labels:
        app: audio-extract
    spec:
      containers:
      - name: audio-extract
        image: gcr.io/my-project/audio-extract:latest
        env:
        - name: GOOGLE_APPLICATION_CREDENTIALS
          value: /secrets/gcp/credentials.json
        volumeMounts:
        - name: gcp-creds
          mountPath: /secrets/gcp
          readOnly: true
        - name: config
          mountPath: /config
          readOnly: true
      volumes:
      - name: gcp-creds
        secret:
          secretName: gcp-credentials
      - name: config
        configMap:
          name: audio-extract-config
```

## Monitoring and Alerting

### 1. Metrics Collection

```python
# audio_extract/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
files_processed = Counter('audio_extract_files_processed_total', 
                         'Total files processed', ['status'])
processing_duration = Histogram('audio_extract_processing_duration_seconds',
                               'Time spent processing files')
active_downloads = Gauge('audio_extract_active_downloads',
                        'Number of active downloads')
```

### 2. Health Check Endpoint

```python
# audio_extract/health.py
@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    checks = {
        'database': check_database_connection(),
        'gcs': check_gcs_access(),
        'drive': check_drive_access(),
        'ffmpeg': check_ffmpeg_available()
    }
    
    status = 'healthy' if all(checks.values()) else 'unhealthy'
    return jsonify({
        'status': status,
        'checks': checks,
        'timestamp': datetime.now().isoformat()
    }), 200 if status == 'healthy' else 503
```

### 3. Logging Enhancement

```yaml
# Enhanced logging configuration
logging:
  version: 1
  formatters:
    json:
      class: pythonjsonlogger.jsonlogger.JsonFormatter
      format: "%(timestamp)s %(level)s %(name)s %(message)s"
  handlers:
    console:
      class: logging.StreamHandler
      formatter: json
    file:
      class: logging.handlers.RotatingFileHandler
      formatter: json
      filename: /var/log/audio-extract/app.log
      maxBytes: 104857600  # 100MB
      backupCount: 10
  root:
    level: INFO
    handlers: [console, file]
```

### 4. Alerting Rules

```yaml
# Prometheus alerting rules
groups:
  - name: audio_extract
    rules:
    - alert: HighFailureRate
      expr: rate(audio_extract_files_processed_total{status="failed"}[5m]) > 0.1
      for: 10m
      annotations:
        summary: "High audio extraction failure rate"
        
    - alert: NoNewFiles
      expr: rate(audio_extract_files_processed_total[1h]) == 0
      for: 2h
      annotations:
        summary: "No files processed in 2 hours"
```

## Performance Optimization

### 1. Parallel Processing

```python
# Enhanced monitor with parallel processing
class EnhancedMonitor:
    def __init__(self, max_workers: int = 3):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def process_files(self, files: List[DriveFile]):
        """Process multiple files in parallel."""
        futures = []
        for file in files:
            future = self.executor.submit(self.process_single_file, file)
            futures.append(future)
        
        # Wait for completion with progress
        for future in as_completed(futures):
            try:
                result = future.result()
                logger.info(f"Processed: {result}")
            except Exception as e:
                logger.error(f"Processing failed: {e}")
```

### 2. Caching Strategy

```python
# Add caching for frequently accessed data
from functools import lru_cache
import redis

class CachedDriveClient:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
    
    @lru_cache(maxsize=100)
    def get_folder_contents(self, folder_id: str):
        """Cache folder contents for 5 minutes."""
        cache_key = f"folder:{folder_id}"
        cached = self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        contents = self.drive_client.list_files(folder_id)
        self.redis.setex(cache_key, 300, json.dumps(contents))
        return contents
```

## Testing Strategy

### 1. Unit Tests
- Test GCS upload/download functionality
- Mock GCS client for offline testing
- Test metric collection
- Verify health check logic

### 2. Integration Tests
- End-to-end flow with real GCS bucket
- Docker container testing
- Monitoring endpoint verification
- Error recovery scenarios

### 3. Load Testing
```bash
# Simulate high load
locust -f load_tests.py --host=http://localhost:8080 --users=100 --spawn-rate=10
```

## Security Considerations

### 1. Credential Management
- Use Workload Identity for GKE deployments
- Rotate service account keys regularly
- Minimal permissions (only required Drive folders and GCS buckets)
- Separate credentials for Drive and GCS

### 2. Access Control
- GCS bucket with private access by default
- Signed URLs for temporary access
- Audit logging for all operations
- VPC Service Controls for additional security

### 3. Data Protection
- Encryption at rest (GCS default)
- Encryption in transit (HTTPS)
- No sensitive data in logs
- Regular security scanning of Docker images

## Quick Development Setup with gcsfuse

Here's how to get started with GCS storage in development:

```bash
# 1. Create GCS bucket (one-time setup)
gsutil mb -p YOUR_PROJECT_ID gs://your-audio-extracts-dev

# 2. Install gcsfuse (see installation instructions above)

# 3. Mount the bucket
mkdir -p ~/audio-extracts-mount
gcsfuse --implicit-dirs your-audio-extracts-dev ~/audio-extracts-mount

# 4. Update dev config to use mount
# Edit audio_extract_config.dev.yaml:
#   output_directory: ~/audio-extracts-mount/dev

# 5. Run audio_extract normally
python -m audio_extract.cli.monitor --config audio_extract_config.dev.yaml

# Files will appear in GCS automatically!
# Check with: gsutil ls -la gs://your-audio-extracts-dev/dev/
```

## Implementation Summary

### Completed Features

1. **Storage Abstraction** ✅
   - Created storage module with abstract interface
   - Implemented LocalStorageAdapter for filesystem
   - Implemented GCSStorageAdapter for Google Cloud Storage
   - Created StorageFactory for easy configuration
   - Full test coverage for all storage adapters

2. **Enhanced Monitoring** ✅
   - Updated DriveMonitor to use storage abstraction
   - Created StorageAwareDriveMonitor for cloud storage
   - Enhanced tracker with GCS metadata fields
   - Added database migrations system

3. **Health Monitoring** ✅
   - Created health check endpoints (/health, /ready, /live)
   - Integrated with CLI monitor
   - Added health checker for all components
   - Flask-based health server on separate port

4. **Docker Support** ✅
   - Created Dockerfile with FFmpeg and non-root user
   - Development docker-compose.yml
   - Production docker-compose.prod.yml with Nginx
   - Health check integration
   - Resource limits and logging

5. **Testing** ✅
   - Comprehensive storage module tests
   - Integration tests for storage with monitor
   - Updated existing tests for new functionality

6. **Documentation** ✅
   - Updated README with storage options
   - Added Docker deployment instructions
   - Created storage example script
   - Enhanced API documentation

7. **Developer Experience** ✅
   - Created comprehensive Makefile with all commands
   - Organized commands by category (setup, testing, development, docker, etc.)
   - Added helpful shortcuts and validation commands
   - Included setup helpers for GCS and development environment

## Dashboard Enhancements (COMPLETED)

### Overview
Added health status information and shareable GCS URLs to the audio extraction dashboard.

### Completed Features

1. **Health Check Endpoint** ✅
   - Added `/api/health` endpoint to check system status
   - Monitors FFmpeg, Database, Storage, and Temp Storage
   - Returns component-level health with detailed messages

2. **Storage URL Integration** ✅
   - Enhanced `/api/recent` and `/api/failed` to include storage URLs
   - Added `/api/refresh-url` for refreshing expired signed URLs
   - Storage information extracted from metadata and included in responses

3. **Dashboard UI Updates** ✅
   - Added health status section with visual indicators (🟢/🔴/🟡)
   - Added "Audio Link" column to recent processing table
   - Implemented download links with file names
   - Added copy-to-clipboard functionality for sharing URLs

4. **Testing** ✅
   - Created comprehensive tests for health endpoint
   - Created tests for storage URL functionality
   - All existing tests still pass

### Implementation Details

- **Backend**: Updated `dashboard/server.py` to add health checks and include storage URLs
- **Frontend**: Enhanced HTML/CSS/JS to display health status and audio links
- **No Database Changes**: Leveraged existing storage fields from migration v2
- **Test-Driven Development**: Created tests first, then implemented features

### Benefits Achieved
- Real-time visibility into system health
- Direct access to extracted audio files
- Easy sharing of audio URLs
- Better troubleshooting with component health status

## Success Criteria

1. **Reliability**: 99.9% uptime for monitoring service
2. **Performance**: Process audio extraction in <30 seconds per file
3. **Storage**: All audio files successfully uploaded to GCS
4. **Monitoring**: Full visibility into service health and performance
5. **Security**: No credential leaks or unauthorized access
6. **Scalability**: Handle 100+ files per hour without degradation

## GitHub Actions and GCSfuse Integration (COMPLETED)

### Overview
Implemented comprehensive GitHub Actions workflows for CI/CD and updated the deployment to use GCSfuse for transparent cloud storage.

### Completed Features

1. **GitHub Actions Workflows** ✅
   - **Test Workflow**: Enhanced to include audio_extract specific tests
   - **Build Workflow**: Builds and pushes Docker images to GitHub Container Registry
   - **Deploy Workflow**: Automated deployment to staging and production with health checks
   - **Release Workflow**: Version management with changelog generation

2. **GCSfuse Docker Integration** ✅
   - Updated Dockerfile with gcsfuse installation and FUSE support
   - Created docker-entrypoint.sh for automatic GCS bucket mounting
   - Added proper signal handling with tini
   - Supports both root and non-root user execution

3. **Configuration Updates** ✅
   - Updated dev/prod/staging configs for GCSfuse paths
   - Added fallback paths for non-containerized deployments
   - Environment variable substitution for sensitive values
   - GCS mount options optimized for each environment

4. **Docker Compose Enhancements** ✅
   - Added privileged mode and FUSE device access
   - Environment-specific compose files (dev, staging, prod)
   - Health checks integrated
   - Resource limits defined

### Benefits of GCSfuse Approach

1. **Zero Code Changes**: Application writes to "local" filesystem that's actually GCS
2. **Automatic Sync**: Files appear in GCS immediately
3. **Cost Effective**: No API calls for uploads, only storage costs
4. **Simple Development**: Same code path for local and cloud storage
5. **Easy Recovery**: Files persist in GCS even if container crashes

### Deployment Process

1. **Development**:
   ```bash
   # Without GCS
   docker-compose up
   
   # With GCS
   ENABLE_GCSFUSE=true GCS_BUCKET_NAME=my-bucket docker-compose up
   ```

2. **Staging/Production**:
   - Push code to main branch
   - GitHub Actions builds and pushes Docker image
   - Deploy workflow automatically deploys to staging
   - Manual approval required for production
   - Health checks verify deployment

### Storage Structure in GCS

```
audio-extracts-bucket/
├── dev/
│   └── 2025/01/meeting_audio.mp3
├── staging/
│   └── 2025/01/meeting_audio.mp3
└── prod/
    └── 2025/01/meeting_audio.mp3
```

## Next Steps for Production

1. **GCS Setup**
   - Create GCP project and enable Storage API
   - Create storage buckets (dev and prod)
   - Set up service account with minimal permissions
   - Test gcsfuse mounting in development

2. **Deployment**
   - Build and push Docker images to registry
   - Deploy to staging environment
   - Run integration tests with real GCS
   - Monitor performance and costs

3. **Optimization** (Future)
   - Implement parallel processing (already stubbed)
   - Add Redis caching for Drive API calls
   - Optimize FFmpeg settings for speed
   - Add compression before GCS upload

---

*This document focuses exclusively on the audio_extract service enhancement for the modularize-june282025 feature branch.*