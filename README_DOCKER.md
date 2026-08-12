# Docker Deployment Guide

This guide explains how to run the Vaultwarden backup script in Docker with automated cron scheduling.

## Quick Start

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your credentials:**
   ```bash
   nano .env  # or use any text editor
   ```

3. **Build and run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

4. **View logs:**
   ```bash
   docker-compose logs -f
   ```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CRON_SCHEDULE` | Cron schedule expression | `0 2 * * *` (daily at 2 AM) |
| `TZ` | Timezone for cron schedule | `America/New_York`, `Europe/London`, `UTC` |
| `RUN_ON_STARTUP` | Run backup immediately when container starts | `true` or `false` |
| `SKIP_CONFIRMATION` | Skip deletion confirmation (required for automation) | `true` |
| `LOCAL_VAULTWARDEN_URL` | URL of your Vaultwarden instance | `http://vaultwarden:8080` |
| `LOCAL_VAULTWARDEN_EMAIL` | Vaultwarden login email | `user@example.com` |
| `LOCAL_MASTER_PASSWORD` | Vaultwarden master password | `your_password` |
| `CLOUD_MASTER_PASSWORD` | Bitwarden Cloud master password | `your_password` |
| `BW_CLIENTID` | Bitwarden API client ID | `user.xxxxxxxx` |
| `BW_CLIENTSECRET` | Bitwarden API client secret | `xxxxxxxxxx` |

### Cron Schedule Examples

```bash
# Every day at 2 AM
CRON_SCHEDULE=0 2 * * *

# Every 6 hours
CRON_SCHEDULE=0 */6 * * *

# Every Sunday at midnight
CRON_SCHEDULE=0 0 * * 0

# Every 30 minutes (for testing)
CRON_SCHEDULE=*/30 * * * *

# Twice daily (2 AM and 2 PM)
CRON_SCHEDULE=0 2,14 * * *
```

**Note:** Do not use quotes in your `.env` file - the values are automatically quoted by docker-compose.

### Timezone Configuration

The `TZ` environment variable sets the timezone for the cron schedule. By default, it's set to `UTC`.

**Common timezone examples:**
```bash
# United States
TZ=America/New_York        # Eastern Time
TZ=America/Chicago         # Central Time
TZ=America/Denver          # Mountain Time
TZ=America/Los_Angeles     # Pacific Time

# Europe
TZ=Europe/London           # UK
TZ=Europe/Paris            # Central European Time
TZ=Europe/Berlin           # Germany

# Asia/Pacific
TZ=Asia/Tokyo              # Japan
TZ=Asia/Shanghai           # China
TZ=Australia/Sydney        # Australia

# UTC (default)
TZ=UTC
```

**Full list of timezones:** https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

**Example:** To run backup daily at 2 AM Eastern Time:
```bash
CRON_SCHEDULE=0 2 * * *
TZ=America/New_York
```

## Docker Commands

### Using Docker Compose (Recommended)

```bash
# Build and start container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop container
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Run backup manually (in addition to cron schedule)
docker-compose exec vw-backup python /app/main.py
```

### Using Docker CLI

```bash
# Build image
docker build -t vw-backup .

# Run container
docker run -d \
  --name vaultwarden-backup \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  vw-backup

# View logs
docker logs -f vaultwarden-backup

# Stop and remove container
docker stop vaultwarden-backup
docker rm vaultwarden-backup
```

## Testing

### Test with immediate execution

Set `RUN_ON_STARTUP=true` in your `.env` file to run the backup immediately when the container starts:

```bash
docker-compose up
```

Watch the logs to ensure it completes successfully, then set `RUN_ON_STARTUP=false` for production use.

### Test cron schedule

Set a frequent schedule for testing (e.g., every 5 minutes):

```bash
CRON_SCHEDULE="*/5 * * * *"
```

Monitor logs:
```bash
docker-compose logs -f
```

Once verified, change to your production schedule.

## Troubleshooting

### View cron logs inside container

```bash
docker-compose exec vw-backup cat /var/log/cron.log
```

### Check if cron is running

```bash
docker-compose exec vw-backup pgrep cron
```

### Verify environment variables

```bash
docker-compose exec vw-backup env | grep -E '(LOCAL|CLOUD|BW_)'
```

### Manual backup execution

```bash
docker-compose exec vw-backup python /app/main.py
```

### Check Bitwarden CLI

```bash
docker-compose exec vw-backup bw --version
```

## Security Notes

1. **Protect your `.env` file** - Never commit it to version control
2. **Use Docker secrets** for production (instead of environment variables)
3. **Limit container permissions** - Run as non-root user if possible
4. **Regularly update** the Bitwarden CLI version in the Dockerfile
5. **Monitor logs** - Check `/app/logs` directory regularly

## Production Deployment

For production use:

1. Set `SKIP_CONFIRMATION=true` (required for automation)
2. Set appropriate `CRON_SCHEDULE` (e.g., daily at off-peak hours)
3. Set `RUN_ON_STARTUP=false` (unless you want immediate backup)
4. Configure `restart: unless-stopped` in docker-compose.yml (already set)
5. Set up external monitoring/alerting for failed backups
6. Regularly review logs in `./logs` directory

## Updating

To update the script or dependencies:

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose up -d --build
```

## Network Configuration

If your Vaultwarden instance is running in Docker on the same host:

1. Create a shared network:
   ```bash
   docker network create vaultwarden-net
   ```

2. Add to docker-compose.yml:
   ```yaml
   networks:
     - vaultwarden-net
   
   networks:
     vaultwarden-net:
       external: true
   ```

3. Use the container name as the URL:
   ```bash
   LOCAL_VAULTWARDEN_URL=http://vaultwarden:80
   ```
