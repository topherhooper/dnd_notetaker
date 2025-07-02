#!/usr/bin/env python3
"""Simple health check server using built-in HTTP server."""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            response = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "audio-extract"
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/':
            response = {
                "message": "Audio Extract Service",
                "endpoints": ["/health"]
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Override to use logging instead of print."""
        logger.info("%s - %s" % (self.address_string(), format % args))

if __name__ == "__main__":
    port = 8081
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"Starting health check server on port {port}")
    server.serve_forever()