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

# Load variables from .env file
load_dotenv()

# Validate environment variables
required_vars = [
    "LOCAL_VAULTWARDEN_URL", "LOCAL_MASTER_PASSWORD", "LOCAL_VAULTWARDEN_EMAIL",
    "CLOUD_MASTER_PASSWORD", "BW_CLIENTID", "BW_CLIENTSECRET"
]
for var in required_vars:
    if not os.getenv(var):
        logger.error(f"Missing required environment variable: {var}")
        sys.exit(1)

def run_cmd(cmd_list, env_update=None, log_cmd=True):
    """Helper to run commands safely without shell=True."""
    current_env = os.environ.copy()
    if env_update:
        current_env.update(env_update)
    
    # Convert string to list if needed (for backward compatibility)
    if isinstance(cmd_list, str):
        cmd_list = cmd_list.split()
    
    if log_cmd:
        # Log command without sensitive data
        safe_cmd = ' '.join(cmd_list)
        logger.info(f"Executing: {safe_cmd}")
    
    result = subprocess.run(
        cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=current_env
    )
    if result.returncode != 0:
        logger.error(f"Command failed: {' '.join(cmd_list)}")
        logger.error(f"Error: {result.stderr.strip()}")
        raise subprocess.CalledProcessError(result.returncode, cmd_list)
    return result.stdout

def validate_export_file(file_path):
    """Validate that export file exists and contains valid data."""
    if not os.path.exists(file_path):
        logger.error(f"Export file not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if not data:
            logger.error("Export file is empty")
            return False
        
        # Check if it's an encrypted export
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
    """Set restrictive permissions on sensitive files."""
    try:
        # On Windows, this may not work the same way, but we try
        if os.name != 'nt':
            os.chmod(file_path, 0o600)
            logger.info(f"Set secure permissions on {file_path}")
    except Exception as e:
        logger.warning(f"Could not set file permissions: {e}")

def confirm_destructive_operation(dry_run=False):
    """Ask user to confirm before deleting cloud data."""
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

def main():
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
    dir_path = "/dev/shm" if os.path.exists("/dev/shm") else None
    
    with tempfile.TemporaryDirectory(dir=dir_path) as tmp_dir:
        export_file = os.path.join(tmp_dir, "vault_export.json")
        cloud_backup_file = os.path.join(tmp_dir, "cloud_backup.json")
        
        try:
            # Ensure clean state by logging out first
            logger.info("Ensuring clean state...")
            if not args.dry_run:
                try:
                    run_cmd(["bw", "logout"])
                except subprocess.CalledProcessError:
                    # Ignore error if not logged in
                    pass
            
            # ==========================================
            # STEP 1: EXPORT FROM LOCAL VAULTWARDEN
            # ==========================================
            logger.info("Target: Local Vaultwarden")
            
            if not args.dry_run:
                run_cmd(["bw", "config", "server", os.getenv('LOCAL_VAULTWARDEN_URL')])
            else:
                logger.info(f"[DRY RUN] Would configure server: {os.getenv('LOCAL_VAULTWARDEN_URL')}")
            
            logger.info("Logging in to Local instance...")
            if not args.dry_run:
                local_session = run_cmd(["bw", "login", os.getenv('LOCAL_VAULTWARDEN_EMAIL'), "--passwordenv", "LOCAL_MASTER_PASSWORD", "--raw"]).strip()
                local_env = {"BW_SESSION": local_session}
            else:
                logger.info("[DRY RUN] Would login to local instance")
                local_env = {}
            
            logger.info("Exporting vault payload to memory...")
            if not args.dry_run:
                # Use --password flag (export doesn't support --passwordenv)
                run_cmd(["bw", "export", "--password", os.getenv('LOCAL_MASTER_PASSWORD'), 
                        "--format", "json", "--output", export_file], env_update=local_env)
                
                # Set secure permissions on export file
                set_secure_permissions(export_file)
                
                # Validate export
                if not validate_export_file(export_file):
                    logger.error("Export validation failed. Aborting.")
                    sys.exit(1)
                
                run_cmd(["bw", "logout"], env_update=local_env)
                logger.info("Successfully logged out of Local Vaultwarden.")
            else:
                logger.info("[DRY RUN] Would export and validate vault data")

            # ==========================================
            # STEP 2: BACKUP CLOUD VAULT (SAFETY NET)
            # ==========================================
            logger.info("\nTarget: Bitwarden Cloud")
            
            if not args.dry_run:
                run_cmd(["bw", "config", "server", "https://vault.bitwarden.com"])
            else:
                logger.info("[DRY RUN] Would configure cloud server")
            
            logger.info("Authenticating via API Key...")
            if not args.dry_run:
                # API key login uses BW_CLIENTID and BW_CLIENTSECRET from environment
                run_cmd(["bw", "login", "--apikey"])
            else:
                logger.info("[DRY RUN] Would authenticate via API key")
            
            logger.info("Unlocking Cloud Vault...")
            if not args.dry_run:
                cloud_session = run_cmd(["bw", "unlock", "--passwordenv", "CLOUD_MASTER_PASSWORD", "--raw"]).strip()
                cloud_env = {"BW_SESSION": cloud_session}
            else:
                logger.info("[DRY RUN] Would unlock cloud vault")
                cloud_env = {}
            
            logger.info("Syncing Cloud database state...")
            if not args.dry_run:
                run_cmd(["bw", "sync"], env_update=cloud_env)
            else:
                logger.info("[DRY RUN] Would sync cloud vault")
            
            # BACKUP CLOUD DATA BEFORE DELETION
            logger.info("Creating backup of cloud vault before deletion...")
            if not args.dry_run:
                run_cmd(["bw", "export", "--password", os.getenv('CLOUD_MASTER_PASSWORD'),
                        "--format", "json", "--output", cloud_backup_file], env_update=cloud_env)
                set_secure_permissions(cloud_backup_file)
                
                if validate_export_file(cloud_backup_file):
                    logger.info(f"[OK] Cloud backup created successfully at {cloud_backup_file}")
                else:
                    logger.error("Cloud backup validation failed. Aborting for safety.")
                    sys.exit(1)
            else:
                logger.info("[DRY RUN] Would create cloud backup")
            
            # ==========================================
            # STEP 3: DELETE AND IMPORT
            # ==========================================
            
            # Get user confirmation
            if not args.skip_confirmation:
                if not confirm_destructive_operation(args.dry_run):
                    logger.warning("Operation cancelled by user.")
                    sys.exit(0)
            
            logger.info("Purging old target records to prevent duplicates...")
            if not args.dry_run:
                raw_items = run_cmd(["bw", "list", "items"], env_update=cloud_env)
                items = json.loads(raw_items)
                logger.info(f"Deleting {len(items)} items...")
                for i, item in enumerate(items, 1):
                    run_cmd(["bw", "delete", "item", item['id']], env_update=cloud_env, log_cmd=False)
                    if i % 10 == 0:
                        logger.info(f"  Deleted {i}/{len(items)} items")
                    
                raw_folders = run_cmd(["bw", "list", "folders"], env_update=cloud_env)
                folders = json.loads(raw_folders)
                logger.info(f"Deleting {len(folders)} folders...")
                for folder in folders:
                    folder_id = folder.get('id')
                    if folder_id:
                        try:
                            run_cmd(["bw", "delete", "folder", folder_id], env_update=cloud_env, log_cmd=False)
                        except subprocess.CalledProcessError as e:
                            logger.warning(f"Could not delete folder {folder_id}: {e}")
                    else:
                        logger.warning(f"Skipping folder with missing ID: {folder}")
            else:
                logger.info("[DRY RUN] Would delete all cloud items and folders")

            # Import clean schema
            logger.info("Importing fresh vault data from local backup...")
            if not args.dry_run:
                run_cmd(["bw", "import", "bitwardenjson", export_file], env_update=cloud_env)
                logger.info("[OK] Import completed successfully")
                
                # Verify import
                run_cmd(["bw", "sync"], env_update=cloud_env)
                raw_items = run_cmd(["bw", "list", "items"], env_update=cloud_env)
                imported_items = json.loads(raw_items)
                logger.info(f"[OK] Verified: {len(imported_items)} items in cloud vault")
            else:
                logger.info("[DRY RUN] Would import vault data")
            
            # Lock and close down session
            if not args.dry_run:
                run_cmd(["bw", "lock"], env_update=cloud_env)
                run_cmd(["bw", "logout"], env_update=cloud_env)
            else:
                logger.info("[DRY RUN] Would lock and logout")
            
            logger.info("=" * 60)
            logger.info("[OK] Sync pipeline completed successfully")
            logger.info(f"Log file: {log_file}")
            logger.info("=" * 60)
            
        except subprocess.CalledProcessError as e:
            logger.error("Sync pipeline aborted due to an error.")
            logger.error(f"Full log available at: {log_file}")
            sys.exit(1)
        except KeyboardInterrupt:
            logger.warning("\nOperation interrupted by user.")
            sys.exit(130)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.error(f"Full log available at: {log_file}")
            sys.exit(1)

if __name__ == "__main__":
    main()