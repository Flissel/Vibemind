"""
Migration script to import secrets from secrets.json into encrypted SQLite database
"""
import sys
import os
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.security.secrets_manager import SecretsManager


def migrate_secrets():
    """Migrate secrets from secrets.json to encrypted SQLite database"""

    # Locate secrets.json
    project_root = Path(__file__).resolve().parents[2]
    secrets_json_path = project_root / 'src' / 'MCP PLUGINS' / 'servers' / 'secrets.json'

    if not secrets_json_path.exists():
        print(f"[X] secrets.json not found at {secrets_json_path}")
        print("No secrets to migrate.")
        return

    print(f"[*] Found secrets.json at {secrets_json_path}")

    # Initialize secrets manager
    print("[*] Initializing encrypted secrets manager...")
    secrets_mgr = SecretsManager()

    # Import secrets
    print("[*] Importing secrets...")
    successful, failed = secrets_mgr.import_from_json(secrets_json_path)

    print(f"\n[+] Migration complete!")
    print(f"   - Successfully imported: {successful} secrets")
    print(f"   - Failed: {failed} secrets")

    # List all secrets (without values)
    secrets_list = secrets_mgr.list_secrets()
    print(f"\n[*] Total secrets in database: {len(secrets_list)}")

    if secrets_list:
        print("\nSecrets by server:")
        current_server = None
        for secret in secrets_list:
            if secret['server_name'] != current_server:
                current_server = secret['server_name']
                print(f"\n  {current_server}:")
            print(f"    - {secret['key_name']}")

    # Verify database path
    db_path = project_root / 'data' / 'secrets.db'
    print(f"\n[*] Database location: {db_path}")
    if db_path.exists():
        print(f"   Database size: {db_path.stat().st_size} bytes")

    print("\n[!] IMPORTANT: secrets.json should now be backed up and removed from the repository.")
    print("   All secrets are now encrypted in SQLite at data/secrets.db")


if __name__ == "__main__":
    migrate_secrets()
