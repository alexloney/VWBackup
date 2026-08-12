# Vaultwarden to Bitwarden Cloud Backup

A Python script that automates backing up a self-hosted [Vaultwarden](https://github.com/dani-garcia/vaultwarden) instance to [Bitwarden Cloud](https://bitwarden.com/).

## 🐳 Quick Start with Docker

For automated scheduled backups, see [README_DOCKER.md](README_DOCKER.md) for full Docker deployment instructions.

```bash
cp .env.example .env
# Edit .env with your credentials
docker-compose up -d
```

## ⚠️ Warning

**This script performs DESTRUCTIVE operations!**

- It will **DELETE ALL** existing data in your Bitwarden Cloud vault before importing the local backup
- Always verify the backup completed successfully before proceeding
- Test with `--dry-run` first to understand what will happen
- The cloud vault backup is only kept temporarily during execution

## Features

- ✅ Automated export from local Vaultwarden instance
- ✅ Safety backup of existing cloud vault before deletion
- ✅ Complete replacement of cloud vault with local data
- ✅ Comprehensive validation and error handling
- ✅ Secure temporary file handling (RAM storage on Linux)
- ✅ Detailed logging to both console and file
- ✅ Dry-run mode for testing
- ✅ Password masking in logs
- ✅ User confirmation before destructive operations

## Prerequisites

### Required Software

1. **Python 3.6 or higher**
   ```bash
   python --version
   ```

2. **Bitwarden CLI (`bw`)**
   - Download from: https://bitwarden.com/help/cli/
   - Verify installation:
     ```bash
     bw --version
     ```

3. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or install manually:
   ```bash
   pip install python-dotenv
   ```

### Required Credentials

1. **Local Vaultwarden Instance**
   - Server URL (e.g., `https://vaultwarden.example.com`)
   - Email/username
   - Master password

2. **Bitwarden Cloud Account**
   - Master password
   - API credentials (Client ID and Client Secret)
     - Get these from: https://vault.bitwarden.com/#/settings/account
     - Click "View API Key" under "API Key" section

## Installation

1. **Clone or download this repository**
   ```bash
   git clone <repository-url>
   cd VWBackup
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** from the example template:
   ```bash
   # Linux/macOS
   cp .env.example .env
   
   # Windows (PowerShell)
   Copy-Item .env.example .env
   
   # Windows (Command Prompt)
   copy .env.example .env
   ```
   
   Then edit `.env` with your actual credentials:
   ```env
   # Local Vaultwarden Configuration
   LOCAL_VAULTWARDEN_URL=https://vaultwarden.example.com
   LOCAL_VAULTWARDEN_EMAIL=your-email@example.com
   LOCAL_MASTER_PASSWORD=your-local-master-password

   # Bitwarden Cloud Configuration
   CLOUD_MASTER_PASSWORD=your-cloud-master-password
   BW_CLIENTID=user.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   BW_CLIENTSECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   
   # Optional: Skip confirmation prompt for automation (USE WITH CAUTION)
   # SKIP_CONFIRMATION=true
   ```

4. **Secure the `.env` file** (Unix/Linux/macOS)
   ```bash
   chmod 600 .env
   ```

## Usage

### Basic Usage

```bash
python main.py
```

This will:
1. Export data from your local Vaultwarden
2. Backup your current cloud vault
3. Ask for confirmation (type `DELETE` to proceed)
4. Delete all cloud vault data
5. Import the local backup to cloud
6. Verify the import

### Dry Run (Recommended First)

Test the script without making any changes:

```bash
python main.py --dry-run
```

This shows what would happen without actually modifying any data.

### Skip Confirmation Prompt

For automation and Docker environments, you have two options:

**Option 1: Environment Variable (Recommended for Docker/Automation)**

Set `SKIP_CONFIRMATION=true` in your `.env` file or Docker environment:

```env
SKIP_CONFIRMATION=true
```

Then run normally:
```bash
python main.py
```

**Option 2: Command-line Flag**

⚠️ **Use with extreme caution!**

```bash
python main.py --skip-confirmation
```

Both options bypass the confirmation prompt and proceed directly with deletion.

### Help

```bash
python main.py --help
```

## How It Works

### Workflow

```
┌─────────────────────────────────────────────┐
│ 1. Logout (clean state)                     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 2. Connect to Local Vaultwarden             │
│    - Configure server URL                    │
│    - Login with credentials                  │
│    - Export vault to temporary file          │
│    - Validate export                         │
│    - Logout                                  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 3. Connect to Bitwarden Cloud               │
│    - Configure cloud server                  │
│    - Login with API key                      │
│    - Unlock vault                            │
│    - Sync latest data                        │
│    - Backup current cloud vault              │
│    - Validate backup                         │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 4. Ask for User Confirmation                │
│    (Type 'DELETE' to proceed)               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 5. Delete All Cloud Data                    │
│    - Delete all items                        │
│    - Delete all folders                      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 6. Import Local Backup                      │
│    - Import vault data                       │
│    - Sync                                    │
│    - Verify import                           │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 7. Cleanup                                   │
│    - Lock vault                              │
│    - Logout                                  │
│    - Delete temporary files                  │
└─────────────────────────────────────────────┘
```

### Security Features

1. **Temporary File Storage**
   - On Linux: Files stored in `/dev/shm` (RAM) to avoid disk writes
   - On Windows: System temp directory
   - Files automatically deleted after execution

2. **Password Protection**
   - Passwords stored in `.env` file (keep this secure!)
   - Passwords masked in log output (`***`)
   - Session tokens used for authentication

3. **File Permissions**
   - Export files set to 0600 (owner read/write only) on Unix/Linux
   - Prevents unauthorized access to temporary vault exports

4. **Validation**
   - Exports validated before proceeding
   - Cloud backup validated before deletion
   - Import verified after completion

## Logging

Logs are written to two places:

1. **Console** - Real-time progress updates
2. **Log Files** - Detailed logs in `logs/` directory
   - Format: `vw_backup_YYYYMMDD_HHMMSS.log`
   - Contains full command output and error details

## Troubleshooting

### "Missing required environment variable"

Make sure your `.env` file contains all required variables and is in the same directory as `main.py`.

### "Command failed: bw login"

- Verify your credentials are correct
- Ensure Bitwarden CLI is installed and in PATH
- Check that your Vaultwarden server is accessible

### "Export validation failed"

- Check that your vault is not empty
- Verify you have read permissions on your local Vaultwarden
- Ensure the master password is correct

### "Could not delete folder"

Some folders may fail to delete if they have dependencies. The script logs warnings but continues. This is usually not a problem as the import will recreate the folder structure.

### Password prompts during execution

If the script pauses waiting for input, it means a password wasn't properly passed via environment variables or STDIN. Check your `.env` file and ensure all passwords are set.

## Automation

### Docker Environment

For Docker deployments, add `SKIP_CONFIRMATION=true` to your environment variables:

**docker-compose.yml example:**
```yaml
version: '3.8'
services:
  vw-backup:
    image: python:3.9
    working_dir: /app
    volumes:
      - .:/app
    environment:
      - LOCAL_VAULTWARDEN_URL=${LOCAL_VAULTWARDEN_URL}
      - LOCAL_VAULTWARDEN_EMAIL=${LOCAL_VAULTWARDEN_EMAIL}
      - LOCAL_MASTER_PASSWORD=${LOCAL_MASTER_PASSWORD}
      - CLOUD_MASTER_PASSWORD=${CLOUD_MASTER_PASSWORD}
      - BW_CLIENTID=${BW_CLIENTID}
      - BW_CLIENTSECRET=${BW_CLIENTSECRET}
      - SKIP_CONFIRMATION=true
    command: python main.py
```

**Dockerfile example:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install Bitwarden CLI
RUN apt-get update && \
    apt-get install -y wget unzip && \
    wget https://vault.bitwarden.com/download/?app=cli&platform=linux -O bw.zip && \
    unzip bw.zip && \
    chmod +x bw && \
    mv bw /usr/local/bin/ && \
    rm bw.zip && \
    apt-get clean

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

CMD ["python", "main.py"]
```

### Scheduled Backups (Linux/macOS)

Create a cron job to run backups automatically. Add `SKIP_CONFIRMATION=true` to your `.env` file first:

```bash
# Edit crontab
crontab -e

# Add line to run daily at 2 AM
0 2 * * * cd /path/to/VWBackup && /usr/bin/python3 main.py >> logs/cron.log 2>&1
```

Or use the command-line flag:

```bash
0 2 * * * cd /path/to/VWBackup && /usr/bin/python3 main.py --skip-confirmation >> logs/cron.log 2>&1
```

### Scheduled Backups (Windows)

**Recommended:** Add `SKIP_CONFIRMATION=true` to your `.env` file, then use Task Scheduler:

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., daily at 2 AM)
4. Action: Start a program
   - Program: `python.exe`
   - Arguments: `main.py`
   - Start in: `C:\path\to\VWBackup`

**Alternative:** Use the `--skip-confirmation` flag:

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., daily at 2 AM)
4. Action: Start a program
   - Program: `python.exe`
   - Arguments: `main.py --skip-confirmation`
   - Start in: `C:\path\to\VWBackup`

**Note:** The environment variable approach is safer as it's explicitly configured in your `.env` file rather than in command arguments.

## Backup Best Practices

1. **Test with `--dry-run` first** to understand the process
2. **Run manually a few times** before automating
3. **Monitor logs** regularly for errors
4. **Keep `.env` file secure** - it contains sensitive credentials
5. **Consider retention** - Cloud vault only keeps the most recent import
6. **Verify imports** periodically by logging into Bitwarden Cloud
7. **Keep local Vaultwarden backed up** separately as well

## Recovery

If something goes wrong during execution:

1. **Check the log file** in the `logs/` directory for details
2. **Cloud backup is temporary** - it exists only during script execution in `/tmp`
3. **Your local Vaultwarden is never modified** by this script
4. **You can re-run the script** to retry the import

To restore from local Vaultwarden after a failed sync:

```bash
python main.py
```

The script will simply re-export from local and try again.

## Limitations

- Does not support organizations or shared collections
- Cloud vault is completely replaced, not merged
- No incremental sync - full replacement only
- Temporary cloud backup is not persisted
- Requires network access to both Vaultwarden and Bitwarden Cloud

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

[Add your license here]

## Author

Alex Loney

## Acknowledgments

- [Vaultwarden](https://github.com/dani-garcia/vaultwarden) - Unofficial Bitwarden server
- [Bitwarden](https://bitwarden.com/) - Password management service
- [Bitwarden CLI](https://bitwarden.com/help/cli/) - Official command-line tool

## Disclaimer

This script is provided as-is without any warranty. Always test thoroughly before using in production. The authors are not responsible for any data loss that may occur from using this script.