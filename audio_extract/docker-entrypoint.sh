#!/bin/bash
set -e

# Docker entrypoint script for audio_extract with GCSfuse support
echo "Starting audio_extract container..."

# Function to unmount on exit
cleanup() {
    echo "Cleaning up..."
    if mountpoint -q /mnt/audio-extracts; then
        echo "Unmounting GCS bucket..."
        fusermount -u /mnt/audio-extracts || true
    fi
}
trap cleanup EXIT

# Check if GCSfuse should be enabled
if [[ "${ENABLE_GCSFUSE}" == "true" ]]; then
    echo "GCSfuse is enabled"
    
    # Check for required environment variables
    if [[ -z "${GCS_BUCKET_NAME}" ]]; then
        echo "ERROR: GCS_BUCKET_NAME environment variable is required when ENABLE_GCSFUSE=true"
        exit 1
    fi
    
    # Check for credentials
    if [[ -z "${GOOGLE_APPLICATION_CREDENTIALS}" ]]; then
        echo "WARNING: GOOGLE_APPLICATION_CREDENTIALS not set, using default credentials"
    else
        if [[ ! -f "${GOOGLE_APPLICATION_CREDENTIALS}" ]]; then
            echo "ERROR: Credentials file not found at ${GOOGLE_APPLICATION_CREDENTIALS}"
            exit 1
        fi
        echo "Using credentials from ${GOOGLE_APPLICATION_CREDENTIALS}"
    fi
    
    # Mount options
    GCSFUSE_OPTS="${GCSFUSE_OPTS:---implicit-dirs --dir-mode=755 --file-mode=644}"
    
    # Add debug flag if requested
    if [[ "${GCSFUSE_DEBUG}" == "true" ]]; then
        GCSFUSE_OPTS="$GCSFUSE_OPTS --debug_gcs --debug_fuse"
    fi
    
    # Create mount point if it doesn't exist
    mkdir -p /mnt/audio-extracts
    
    # Mount the GCS bucket
    echo "Mounting GCS bucket ${GCS_BUCKET_NAME} to /mnt/audio-extracts..."
    if [[ -n "${GOOGLE_APPLICATION_CREDENTIALS}" ]]; then
        gcsfuse --key-file="${GOOGLE_APPLICATION_CREDENTIALS}" ${GCSFUSE_OPTS} "${GCS_BUCKET_NAME}" /mnt/audio-extracts
    else
        gcsfuse ${GCSFUSE_OPTS} "${GCS_BUCKET_NAME}" /mnt/audio-extracts
    fi
    
    # Verify mount
    if mountpoint -q /mnt/audio-extracts; then
        echo "Successfully mounted GCS bucket"
        
        # Create environment-specific subdirectory
        ENV_DIR="${ENVIRONMENT:-dev}"
        mkdir -p "/mnt/audio-extracts/${ENV_DIR}"
        echo "Created directory: /mnt/audio-extracts/${ENV_DIR}"
        
        # Test write access
        if touch "/mnt/audio-extracts/${ENV_DIR}/.mount-test" 2>/dev/null; then
            rm -f "/mnt/audio-extracts/${ENV_DIR}/.mount-test"
            echo "Write access verified"
        else
            echo "WARNING: No write access to mounted bucket"
        fi
    else
        echo "ERROR: Failed to mount GCS bucket"
        exit 1
    fi
else
    echo "GCSfuse is disabled, using local storage"
    
    # Ensure local output directory exists
    mkdir -p /workspace/audio_extract/output
fi

# Update configuration if needed
if [[ "${ENABLE_GCSFUSE}" == "true" ]] && [[ -f "/workspace/audio_extract/configs/audio_extract_config.yaml" ]]; then
    # Check if we need to update the output path in config
    if [[ "${UPDATE_CONFIG_PATH}" == "true" ]]; then
        echo "Updating configuration to use GCS mount..."
        # This would normally use a proper YAML parser, but for simplicity:
        sed -i "s|output_directory:.*|output_directory: /mnt/audio-extracts/${ENVIRONMENT:-dev}|g" /workspace/audio_extract/configs/audio_extract_config.yaml
    fi
fi

# Log the configuration
echo "Configuration:"
echo "  ENABLE_GCSFUSE: ${ENABLE_GCSFUSE}"
echo "  GCS_BUCKET_NAME: ${GCS_BUCKET_NAME}"
echo "  ENVIRONMENT: ${ENVIRONMENT:-dev}"
echo "  Working directory: $(pwd)"
echo "  User: $(whoami)"

# Health check for storage
check_storage_health() {
    if [[ "${ENABLE_GCSFUSE}" == "true" ]]; then
        if mountpoint -q /mnt/audio-extracts; then
            echo "Storage health: OK (GCS mounted)"
            return 0
        else
            echo "Storage health: FAILED (GCS not mounted)"
            return 1
        fi
    else
        if [[ -d /workspace/audio_extract/output ]] && [[ -w /workspace/audio_extract/output ]]; then
            echo "Storage health: OK (local storage)"
            return 0
        else
            echo "Storage health: FAILED (local storage not accessible)"
            return 1
        fi
    fi
}

# Export health check function for the application
export -f check_storage_health

# Start the audio extract service using the virtual environment
echo "Starting audio_extract service..."
cd /workspace/audio_extract
if [[ -f /workspace/audio_extract/venv/bin/python ]]; then
    echo "Using virtual environment Python"
    exec /workspace/audio_extract/venv/bin/python -m audio_extract.cli.monitor "$@"
else
    echo "Using system Python"
    exec python -m audio_extract.cli.monitor "$@"
fi