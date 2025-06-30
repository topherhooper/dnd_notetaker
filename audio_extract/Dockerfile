# Dockerfile for audio_extract service
FROM python:3.9-slim

# Install FFmpeg and other dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 audioextract

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs /app/output && \
    chown -R audioextract:audioextract /app

# Switch to non-root user
USER audioextract

# Expose ports
EXPOSE 8080 8081

# Default command
ENTRYPOINT ["python", "-m", "audio_extract.cli.monitor"]
CMD ["--config", "/app/configs/audio_extract_config.yaml"]