#!/bin/bash
# Entrypoint script to run health server in background

# Start health server in background
echo "Starting health check server..."
python /app/health_server.py &

# Give health server time to start
sleep 2

# Run the main application
echo "Starting main application..."
exec python -m dnd_notetaker "$@"