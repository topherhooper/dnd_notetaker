FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY setup.py .
COPY README.md .

# Install the package
RUN pip install -e .

# Create directories for config and output
RUN mkdir -p /.meat_notes_configs/ /output

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MEET_NOTES_CONFIG=/.meat_notes_configs/config.json
ENV MEET_NOTES_OUTPUT=/meet_notes_output

# Entry point - use the package module
ENTRYPOINT ["python", "-m", "dnd_notetaker"]