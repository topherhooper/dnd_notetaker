#!/usr/bin/env python3
"""Simple health check server for staging deployment."""

from flask import Flask, jsonify
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/health")
def health_check():
    """Basic health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "audio-extract"
    }), 200

@app.route("/")
def index():
    """Root endpoint."""
    return jsonify({
        "message": "Audio Extract Service",
        "endpoints": ["/health"]
    }), 200

if __name__ == "__main__":
    port = 8081
    logger.info(f"Starting health check server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)