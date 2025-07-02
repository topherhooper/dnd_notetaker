#!/bin/bash
# Startup script for GCP Compute Engine instance
# This script runs automatically when the instance starts

set -e

echo "Starting instance configuration..."

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    
    # Add ubuntu user to docker group
    usermod -aG docker ubuntu
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Install necessary packages
apt-get install -y git nginx certbot python3-certbot-nginx

# Create deployment directories
mkdir -p /opt/audio-extract
mkdir -p /opt/audio-extract-pr-staging
chown -R ubuntu:ubuntu /opt/audio-extract*

# Clone the repository (for docker-compose files)
if [ ! -d "/opt/audio-extract/.git" ]; then
    cd /opt/audio-extract
    sudo -u ubuntu git clone https://github.com/topherhooper/dnd_notetaker.git .
fi

# Install Google Cloud SDK (already installed on GCP images)
# This is just to ensure gcloud and gsutil are available

# Configure nginx as reverse proxy
cat > /etc/nginx/sites-available/audio-extract <<EOF
server {
    listen 80;
    server_name _;
    
    # Staging endpoint
    location /staging/ {
        proxy_pass http://localhost:8081/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Production endpoint
    location / {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable the site
ln -sf /etc/nginx/sites-available/audio-extract /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# Create a systemd service to ensure Docker starts
systemctl enable docker
systemctl start docker

# Pull the latest images (will fail on first run, that's OK)
sudo -u ubuntu docker pull ghcr.io/topherhooper/dnd_notetaker/audio-extract:latest || true

echo "Startup script completed successfully!"