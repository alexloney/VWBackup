FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    cron \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install Bitwarden CLI
# Note: Bitwarden only provides x86_64 Linux binaries, so this image only supports linux/amd64
RUN wget https://github.com/bitwarden/clients/releases/download/cli-v2026.7.0/bw-linux-2026.7.0.zip \
    && unzip bw-linux-2026.7.0.zip \
    && chmod +x bw \
    && mv bw /usr/local/bin/ \
    && rm bw-linux-2026.7.0.zip

# Verify bw installation
RUN bw --version

# Set working directory
WORKDIR /app

# Copy Python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY entrypoint.sh /entrypoint.sh

# Make entrypoint executable
RUN chmod +x /entrypoint.sh

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables with defaults
ENV CRON_SCHEDULE="0 2 * * *"
ENV SKIP_CONFIRMATION="true"
ENV RUN_ON_STARTUP="false"
ENV TZ="UTC"

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
