# Dockerfile for audio_extract service with GCSfuse support
FROM python:3.9-slim

# Install dependencies including gcsfuse
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    gnupg \
    lsb-release \
    tini \
    fuse \
    ca-certificates \
    && echo "deb https://packages.cloud.google.com/apt gcsfuse-$(lsb_release -c -s) main" > /etc/apt/sources.list.d/gcsfuse.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update \
    && apt-get install -y gcsfuse \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with access to fuse
RUN useradd -m -u 1000 audioextract && \
    usermod -a -G fuse audioextract

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for data, logs, output, and GCS mount
RUN mkdir -p /app/data /app/logs /app/output /mnt/audio-extracts && \
    chown -R audioextract:audioextract /app /mnt/audio-extracts

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Allow audioextract user to use fusermount
RUN chmod u+s /usr/bin/fusermount

# Switch to non-root user
USER audioextract

# Expose ports
EXPOSE 8080 8081

# Use tini to handle signals properly
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]
CMD ["--config", "/app/configs/audio_extract_config.yaml"]