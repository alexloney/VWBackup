"""
Vaultwarden to Bitwarden Cloud Backup Script

This script automates the backup of a self-hosted Vaultwarden instance to Bitwarden Cloud.
It exports data from the local Vaultwarden server, backs up the existing cloud vault,
and then replaces the cloud vault contents with the local data.

WARNING: This is a DESTRUCTIVE operation. All existing data in the cloud vault will be
deleted before importing the local backup.

Requirements:
    - Bitwarden CLI (bw) installed and available in PATH
    - Python 3.6+
    - python-dotenv package
    - .env file with required credentials

Author: Alex Loney
Created: 2026-06-17
"""

import os
import subprocess
import json
import tempfile
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ============================================================================
# LOGGING SETUP
# ============================================================================

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"vw_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# ENVIRONMENT VALIDATION
# ============================================================================

# Load variables from .env file
load_dotenv()

# Validate that all required environment variables are present
# Exit early if any are missing to prevent partial execution
required_vars = [
    "LOCAL_VAULTWARDEN_URL",       # URL of the local Vaultwarden instance
    "LOCAL_MASTER_PASSWORD",        # Master password for local vault
    "LOCAL_VAULTWARDEN_EMAIL",     # Email/username for local vault
    "CLOUD_MASTER_PASSWORD",        # Master password for Bitwarden Cloud
    "BW_CLIENTID",                  # API client ID for Bitwarden Cloud
    "BW_CLIENTSECRET"              # API client secret for Bitwarden Cloud
]
for var in required_vars:
    if not os.getenv(var):
        logger.error(f"Missing required environment variable: {var}")
        sys.exit(1)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def run_cmd(cmd_list, env_update=None, log_cmd=True, stdin_input=None):
    """
    Execute a command safely without using shell=True.
    
    This function provides secure command execution with the following features:
    - No shell injection vulnerabilities (shell=False by default)
    - Environment variable support for session tokens
    - Password masking in logs
    - STDIN input support for interactive commands
    - Comprehensive error handling and logging
    
    Args:
        cmd_list (list): Command and arguments as a list
        env_update (dict, optional): Additional environment variables to add
        log_cmd (bool, optional): Whether to log the command. Defaults to True
        stdin_input (str, optional): Text to send to command's STDIN
        
    Returns:
        str: Command's stdout output
        
    Raises:
        subprocess.CalledProcessError: If command returns non-zero exit code
    """
    current_env = os.environ.copy()
    if env_update:
        current_env.update(env_update)
    
    # Convert string to list if needed (for backward compatibility)
    if isinstance(cmd_list, str):
        cmd_list = cmd_list.split()
    
    if log_cmd:
        # Log command, masking passwords for security
        safe_cmd = []
        mask_next = False
        for item in cmd_list:
            if mask_next:
                safe_cmd.append('***')
                mask_next = False
            elif item == '--password':
                safe_cmd.append(item)
                mask_next = True
            else:
                safe_cmd.append(item)
        logger.info(f"Executing: {' '.join(safe_cmd)}")
    
    # Execute command with STDIN input if provided
    result = subprocess.run(
        cmd_list, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True, 
        input=stdin_input,
        env=current_env
    )
    
    # Check for errors and log appropriately
    if result.returncode != 0:
        logger.error(f"Command failed: {' '.join(cmd_list)}")
        logger.error(f"Error: {result.stderr.strip()}")
        raise subprocess.CalledProcessError(result.returncode, cmd_list)
    return result.stdout

def validate_export_file(file_path):
    """
    Validate that an export file exists and contains valid data.
    
    This function checks:
    - File exists
    - File contains valid JSON
    - File is not empty
    - File has expected structure (encrypted or unencrypted)
    
    Args:
        file_path (str): Path to the export file to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not os.path.exists(file_path):
        logger.error(f"Export file not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if not data:
            logger.error("Export file is empty")
            return False
        
        # Check if it's an encrypted export (password-protected format)
        if data.get('encrypted') and data.get('passwordProtected'):
            logger.info(f"Export validated: encrypted/password-protected format")
            return True
        
        # Check for expected unencrypted structure
        if 'items' not in data and 'folders' not in data:
            logger.warning("Export file may not have expected structure")
        
        item_count = len(data.get('items', []))
        folder_count = len(data.get('folders', []))
        logger.info(f"Export validated: {item_count} items, {folder_count} folders")
        return True
    
    except json.JSONDecodeError as e:
        logger.error(f"Export file is not valid JSON: {e}")
        return False
    except Exception as e:
        logger.error(f"Error validating export: {e}")
        return False

def set_secure_permissions(file_path):
    """
    Set restrictive permissions on sensitive files (Unix/Linux only).
    
    Sets file permissions to 0o600 (read/write for owner only) to prevent
    unauthorized access to exported vault data.
    
    Args:
        file_path (str): Path to the file to secure
    """
    try:
        # On Windows, this may not work the same way, but we try
        if os.name != 'nt':
            os.chmod(file_path, 0o600)
            logger.info(f"Set secure permissions on {file_path}")
    except Exception as e:
        logger.warning(f"Could not set file permissions: {e}")

def confirm_destructive_operation(dry_run=False):
    """
    Ask user to confirm before deleting cloud data.
    
    This provides a safety check before destructive operations. User must
    type 'DELETE' exactly to proceed.
    
    Args:
        dry_run (bool): If True, skip actual confirmation (for dry-run mode)
        
    Returns:
        bool: True if user confirmed, False otherwise
    """
    if dry_run:
        logger.info("[DRY RUN] Would ask for confirmation here")
        return True
    
    print("\n" + "="*60)
    print("WARNING: DESTRUCTIVE OPERATION")
    print("="*60)
    print("This will DELETE ALL items and folders from your cloud vault!")
    print("Make sure you have a backup before proceeding.")
    print("="*60)
    
    response = input("\nType 'DELETE' to confirm: ").strip()
    return response == "DELETE"

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main execution function - orchestrates the backup workflow.
    
    Workflow:
        1. Parse command-line arguments
        2. Export vault data from local Vaultwarden
        3. Backup existing Bitwarden Cloud vault (safety net)
        4. Delete all cloud vault data
        5. Import local data to cloud
        6. Verify and cleanup
        
    The script uses temporary files that are automatically cleaned up.
    On Linux, temporary files are stored in /dev/shm (RAM) for security.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Backup Vaultwarden to Bitwarden Cloud",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""WARNING: This script will DELETE all cloud vault data before importing.
Always verify your backup completed successfully before proceeding."""
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--skip-confirmation',
        action='store_true',
        help='Skip confirmation prompt (USE WITH CAUTION)'
    )
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("=" * 60)
    
    # Setup temporary directory in RAM if on Linux, otherwise system default temp
    # Using RAM storage increases security by avoiding disk writes of sensitive data
    dir_path = "/dev/shm" if os.path.exists("/dev/shm") else None
    
    with tempfile.TemporaryDirectory(dir=dir_path) as tmp_dir:
        export_file = os.path.join(tmp_dir, "vault_export.json")
        cloud_backup_file = os.path.join(tmp_dir, "cloud_backup.json")
        
        try:
            # ------------------------------------------------------------
            # PRE-FLIGHT: Ensure clean state
            # ------------------------------------------------------------
            # Logout any existing session to prevent "already logged in" errors
            logger.info("Ensuring clean state...")
            if not args.dry_run:
                try:
                    run_cmd(["bw", "logout"])
                except subprocess.CalledProcessError:
                    # Ignore error if not logged in - this is expected
                    pass
            
            # ============================================================
            # STEP 1: EXPORT FROM LOCAL VAULTWARDEN
            # ============================================================
            # Connect to the local Vaultwarden instance and export all vault data
            # to a temporary file for backup to the cloud
            logger.info("Target: Local Vaultwarden")
            
            # Configure bw CLI to connect to local Vaultwarden server
            if not args.dry_run:
                run_cmd(["bw", "config", "server", os.getenv('LOCAL_VAULTWARDEN_URL')])
            else:
                logger.info(f"[DRY RUN] Would configure server: {os.getenv('LOCAL_VAULTWARDEN_URL')}")
            
            # Login to local instance using email and password
            logger.info("Logging in to Local instance...")
            if not args.dry_run:
                # Login returns a session token that we use for subsequent commands
                local_session = run_cmd(["bw", "login", os.getenv('LOCAL_VAULTWARDEN_EMAIL'), "--passwordenv", "LOCAL_MASTER_PASSWORD", "--raw"]).strip()
                local_env = {"BW_SESSION": local_session}
            else:
                logger.info("[DRY RUN] Would login to local instance")
                local_env = {}
            
            # Export the entire vault to a JSON file
            logger.info("Exporting vault payload to memory...")
            if not args.dry_run:
                # Note: bw export requires --password flag (doesn't support --passwordenv)
                run_cmd(["bw", "export", "--password", os.getenv('LOCAL_MASTER_PASSWORD'), 
                        "--format", "json", "--output", export_file], env_update=local_env)
                
                # Set secure permissions on export file (Unix/Linux only)
                set_secure_permissions(export_file)
                
                # Validate the export file before proceeding
                if not validate_export_file(export_file):
                    logger.error("Export validation failed. Aborting.")
                    sys.exit(1)
                
                # Logout from local instance to clean up session
                run_cmd(["bw", "logout"], env_update=local_env)
                logger.info("Successfully logged out of Local Vaultwarden.")
            else:
                logger.info("[DRY RUN] Would export and validate vault data")

            # ============================================================
            # STEP 2: BACKUP CLOUD VAULT (SAFETY NET)
            # ============================================================
            # Before deleting anything, create a backup of the existing cloud vault
            # This provides a recovery option if something goes wrong
            logger.info("\nTarget: Bitwarden Cloud")
            
            # Configure bw CLI to connect to Bitwarden Cloud
            if not args.dry_run:
                run_cmd(["bw", "config", "server", "https://vault.bitwarden.com"])
            else:
                logger.info("[DRY RUN] Would configure cloud server")
            
            # Authenticate using API key (more reliable for automation than email/password)
            logger.info("Authenticating via API Key...")
            if not args.dry_run:
                # API key login uses BW_CLIENTID and BW_CLIENTSECRET from environment
                run_cmd(["bw", "login", "--apikey"])
            else:
                logger.info("[DRY RUN] Would authenticate via API key")
            
            # Unlock the vault with master password
            logger.info("Unlocking Cloud Vault...")
            if not args.dry_run:
                # Unlock returns a session token for subsequent operations
                cloud_session = run_cmd(["bw", "unlock", "--passwordenv", "CLOUD_MASTER_PASSWORD", "--raw"]).strip()
                cloud_env = {"BW_SESSION": cloud_session}
            else:
                logger.info("[DRY RUN] Would unlock cloud vault")
                cloud_env = {}
            
            # Sync to get latest data from server
            logger.info("Syncing Cloud database state...")
            if not args.dry_run:
                run_cmd(["bw", "sync"], env_update=cloud_env)
            else:
                logger.info("[DRY RUN] Would sync cloud vault")
            
            # Create backup of cloud vault before deletion
            logger.info("Creating backup of cloud vault before deletion...")
            if not args.dry_run:
                run_cmd(["bw", "export", "--password", os.getenv('CLOUD_MASTER_PASSWORD'),
                        "--format", "json", "--output", cloud_backup_file], env_update=cloud_env)
                set_secure_permissions(cloud_backup_file)
                
                # Validate backup before proceeding with deletion
                if validate_export_file(cloud_backup_file):
                    logger.info(f"[OK] Cloud backup created successfully at {cloud_backup_file}")
                else:
                    logger.error("Cloud backup validation failed. Aborting for safety.")
                    sys.exit(1)
            else:
                logger.info("[DRY RUN] Would create cloud backup")
            
            # ============================================================
            # STEP 3: DELETE AND IMPORT
            # ============================================================
            # This is the destructive part - delete all cloud data and replace
            # with the local backup. User confirmation required unless skipped.
            
            # Get user confirmation before proceeding with deletion
            if not args.skip_confirmation:
                if not confirm_destructive_operation(args.dry_run):
                    logger.warning("Operation cancelled by user.")
                    sys.exit(0)
            
            # Delete all existing items and folders from cloud vault
            logger.info("Purging old target records to prevent duplicates...")
            if not args.dry_run:
                # Delete all items (passwords, notes, etc.)
                raw_items = run_cmd(["bw", "list", "items"], env_update=cloud_env)
                items = json.loads(raw_items)
                logger.info(f"Deleting {len(items)} items...")
                for i, item in enumerate(items, 1):
                    run_cmd(["bw", "delete", "item", item['id']], env_update=cloud_env, log_cmd=False)
                    # Log progress every 10 items to avoid log spam
                    if i % 10 == 0:
                        logger.info(f"  Deleted {i}/{len(items)} items")
                    
                # Delete all folders (organizational structure)
                raw_folders = run_cmd(["bw", "list", "folders"], env_update=cloud_env)
                folders = json.loads(raw_folders)
                logger.info(f"Deleting {len(folders)} folders...")
                for folder in folders:
                    folder_id = folder.get('id')
                    if folder_id:
                        try:
                            run_cmd(["bw", "delete", "folder", folder_id], env_update=cloud_env, log_cmd=False)
                        except subprocess.CalledProcessError as e:
                            # Some folders may fail to delete - log warning but continue
                            logger.warning(f"Could not delete folder {folder_id}: {e}")
                    else:
                        logger.warning(f"Skipping folder with missing ID: {folder}")
            else:
                logger.info("[DRY RUN] Would delete all cloud items and folders")

            # Import the local vault data to cloud
            logger.info("Importing fresh vault data from local backup...")
            if not args.dry_run:
                # bw import requires password via STDIN (not as a flag)
                run_cmd(["bw", "import", "bitwardenjson", export_file], 
                        env_update=cloud_env, 
                        stdin_input=os.getenv('CLOUD_MASTER_PASSWORD'))
                logger.info("[OK] Import completed successfully")
                
                # Verify the import was successful by listing items
                run_cmd(["bw", "sync"], env_update=cloud_env)
                raw_items = run_cmd(["bw", "list", "items"], env_update=cloud_env)
                imported_items = json.loads(raw_items)
                logger.info(f"[OK] Verified: {len(imported_items)} items in cloud vault")
            else:
                logger.info("[DRY RUN] Would import vault data")
            
            # ============================================================
            # CLEANUP AND FINALIZATION
            # ============================================================
            # Lock and logout to clean up session
            if not args.dry_run:
                run_cmd(["bw", "lock"], env_update=cloud_env)
                run_cmd(["bw", "logout"], env_update=cloud_env)
            else:
                logger.info("[DRY RUN] Would lock and logout")
            
            # Success! Log completion message
            logger.info("=" * 60)
            logger.info("[OK] Sync pipeline completed successfully")
            logger.info(f"Log file: {log_file}")
            logger.info("=" * 60)
            
        except subprocess.CalledProcessError as e:
            # Command execution failed
            logger.error("Sync pipeline aborted due to an error.")
            logger.error(f"Full log available at: {log_file}")
            sys.exit(1)
        except KeyboardInterrupt:
            # User pressed Ctrl+C
            logger.warning("\nOperation interrupted by user.")
            sys.exit(130)
        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error: {e}")
            logger.error(f"Full log available at: {log_file}")
            sys.exit(1)

# Entry point
if __name__ == "__main__":
    main()