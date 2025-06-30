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
    make \
    && echo "deb https://packages.cloud.google.com/apt gcsfuse-$(lsb_release -c -s) main" > /etc/apt/sources.list.d/gcsfuse.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update \
    && apt-get install -y gcsfuse \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and fuse group if it doesn't exist
RUN groupadd -f fuse && \
    useradd -m -u 1000 audioextract && \
    usermod -a -G fuse audioextract

# Set working directory to parent of audio_extract
WORKDIR /workspace

# Create audio_extract directory and copy all code into it
RUN mkdir -p audio_extract
COPY . audio_extract/

# Change to audio_extract directory
WORKDIR /workspace/audio_extract

# Install dependencies using the Makefile (creates venv and installs requirements)
RUN make install

# Install the audio_extract package in editable mode
RUN /workspace/audio_extract/venv/bin/pip install -e .

# Create directories for data, logs, output, and GCS mount
RUN mkdir -p /workspace/audio_extract/data /workspace/audio_extract/logs /workspace/audio_extract/output /mnt/audio-extracts && \
    chown -R audioextract:audioextract /workspace /mnt/audio-extracts

# Set PYTHONPATH so Python can find the audio_extract module
ENV PYTHONPATH=/workspace:$PYTHONPATH

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