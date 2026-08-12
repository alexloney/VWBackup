#!/bin/bash
set -e

# Vaultwarden to Bitwarden Cloud Backup - Docker Entrypoint
# This script sets up and runs the backup on a cron schedule

echo "=========================================="
echo "Vaultwarden Backup - Docker Container"
echo "=========================================="

# Default cron schedule: daily at 2 AM
CRON_SCHEDULE="${CRON_SCHEDULE:-0 2 * * *}"

echo "Cron schedule: $CRON_SCHEDULE"

# Validate required environment variables
REQUIRED_VARS=(
    "LOCAL_VAULTWARDEN_URL"
    "LOCAL_MASTER_PASSWORD"
    "LOCAL_VAULTWARDEN_EMAIL"
    "CLOUD_MASTER_PASSWORD"
    "BW_CLIENTID"
    "BW_CLIENTSECRET"
)

echo "Validating environment variables..."
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "ERROR: Missing required environment variable: $var"
        exit 1
    fi
done
echo "All required environment variables present."

# Create the cron job that runs the backup script
# Export all environment variables to a file that cron can source
echo "Setting up cron job..."

# Create environment file for cron (cron doesn't inherit environment)
printenv | grep -v "no_proxy" > /etc/environment

# Create the cron job
# We need to source the environment and then run the Python script
CRON_CMD="$CRON_SCHEDULE . /etc/environment; cd /app && /usr/local/bin/python main.py >> /var/log/cron.log 2>&1"
echo "$CRON_CMD" > /etc/cron.d/vw-backup

# Set proper permissions
chmod 0644 /etc/cron.d/vw-backup

# Apply cron job
crontab /etc/cron.d/vw-backup

echo "Cron job installed: $CRON_SCHEDULE"

# Create log file
touch /var/log/cron.log

# Option to run immediately on startup
if [ "$RUN_ON_STARTUP" = "true" ]; then
    echo "=========================================="
    echo "Running initial backup (RUN_ON_STARTUP=true)..."
    echo "=========================================="
    cd /app
    python main.py
    echo "Initial backup completed."
    echo "=========================================="
fi

# Start cron in foreground
echo "Starting cron daemon..."
echo "Container is ready. Logs will appear below."
echo "=========================================="

# Start cron and tail the log
cron && tail -f /var/log/cron.log
