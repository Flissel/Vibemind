"""
Secrets manager for secure storage and retrieval of API keys and credentials
"""
import json
import sqlite3
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .encryption import encrypt_value, decrypt_value
from .key_manager import KeyManager


class SecretsManager:
    """Manages encrypted secrets storage in SQLite database"""

    def __init__(self, db_path: Optional[Path] = None, data_dir: Optional[Path] = None):
        """
        Initialize secrets manager.

        Args:
            db_path: Path to SQLite database file (defaults to data/secrets.db)
            data_dir: Path to data directory for key storage
        """
        if db_path is None:
            project_root = Path(__file__).resolve().parents[2]
            db_path = project_root / 'data' / 'secrets.db'

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.key_manager = KeyManager(data_dir)
        self._initialize_database()

    def _initialize_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Secrets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS secrets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name TEXT NOT NULL,
                key_name TEXT NOT NULL,
                encrypted_value BLOB NOT NULL,
                iv BLOB NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(server_name, key_name)
            )
        ''')

        # Audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS secrets_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name TEXT NOT NULL,
                key_name TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')

        # Encryption keys metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS encryption_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_version INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                rotated_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        ''')

        conn.commit()
        conn.close()

    def _log_audit(self, server_name: str, key_name: str, action: str):
        """Log audit entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            'INSERT INTO secrets_audit_log (server_name, key_name, action, timestamp) VALUES (?, ?, ?, ?)',
            (server_name, key_name, action, datetime.utcnow().isoformat())
        )

        conn.commit()
        conn.close()

    def add_secret(self, server_name: str, key_name: str, value: str) -> bool:
        """
        Add or update a secret.

        Args:
            server_name: Name of the MCP server (e.g., "github", "supabase")
            key_name: Name of the credential key (e.g., "GITHUB_TOKEN")
            value: The secret value to encrypt and store

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get master key
            master_key = self.key_manager.get_master_key()

            # Encrypt the value
            ciphertext, iv = encrypt_value(value, master_key)

            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.utcnow().isoformat()

            # Check if secret exists
            cursor.execute(
                'SELECT id FROM secrets WHERE server_name = ? AND key_name = ?',
                (server_name, key_name)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing secret
                cursor.execute(
                    'UPDATE secrets SET encrypted_value = ?, iv = ?, updated_at = ? WHERE server_name = ? AND key_name = ?',
                    (ciphertext, iv, now, server_name, key_name)
                )
                action = 'updated'
            else:
                # Insert new secret
                cursor.execute(
                    'INSERT INTO secrets (server_name, key_name, encrypted_value, iv, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
                    (server_name, key_name, ciphertext, iv, now, now)
                )
                action = 'created'

            conn.commit()
            conn.close()

            # Log audit trail
            self._log_audit(server_name, key_name, action)

            return True

        except Exception as e:
            print(f"Error adding secret: {e}")
            return False

    def get_secret(self, server_name: str, key_name: str) -> Optional[str]:
        """
        Retrieve and decrypt a secret.

        Args:
            server_name: Name of the MCP server
            key_name: Name of the credential key

        Returns:
            Decrypted secret value, or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT encrypted_value, iv FROM secrets WHERE server_name = ? AND key_name = ?',
                (server_name, key_name)
            )
            result = cursor.fetchone()
            conn.close()

            if not result:
                return None

            ciphertext, iv = result

            # Get master key and decrypt
            master_key = self.key_manager.get_master_key()
            plaintext = decrypt_value(ciphertext, iv, master_key)

            return plaintext

        except Exception as e:
            print(f"Error retrieving secret: {e}")
            return None

    def get_server_secrets(self, server_name: str) -> Dict[str, str]:
        """
        Get all secrets for a specific server.

        Args:
            server_name: Name of the MCP server

        Returns:
            Dictionary mapping key names to decrypted values
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT key_name, encrypted_value, iv FROM secrets WHERE server_name = ?',
                (server_name,)
            )
            results = cursor.fetchall()
            conn.close()

            if not results:
                return {}

            # Decrypt all values
            master_key = self.key_manager.get_master_key()
            secrets = {}

            for key_name, ciphertext, iv in results:
                try:
                    plaintext = decrypt_value(ciphertext, iv, master_key)
                    secrets[key_name] = plaintext
                except Exception as e:
                    print(f"Error decrypting {server_name}.{key_name}: {e}")

            return secrets

        except Exception as e:
            print(f"Error retrieving server secrets: {e}")
            return {}

    def list_secrets(self) -> List[Dict[str, str]]:
        """
        List all secrets (without values, just metadata).

        Returns:
            List of secret metadata dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT server_name, key_name, created_at, updated_at FROM secrets ORDER BY server_name, key_name'
            )
            results = cursor.fetchall()
            conn.close()

            secrets = []
            for server_name, key_name, created_at, updated_at in results:
                secrets.append({
                    'server_name': server_name,
                    'key_name': key_name,
                    'created_at': created_at,
                    'updated_at': updated_at
                })

            return secrets

        except Exception as e:
            print(f"Error listing secrets: {e}")
            return []

    def delete_secret(self, server_name: str, key_name: str) -> bool:
        """
        Delete a secret.

        Args:
            server_name: Name of the MCP server
            key_name: Name of the credential key

        Returns:
            True if deleted, False if not found or error
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'DELETE FROM secrets WHERE server_name = ? AND key_name = ?',
                (server_name, key_name)
            )
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()

            if deleted:
                self._log_audit(server_name, key_name, 'deleted')

            return deleted

        except Exception as e:
            print(f"Error deleting secret: {e}")
            return False

    def export_to_json(self, output_path: Path) -> bool:
        """
        Export all secrets to JSON file (decrypted - use with caution).

        Args:
            output_path: Path to output JSON file

        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT DISTINCT server_name FROM secrets ORDER BY server_name')
            servers = [row[0] for row in cursor.fetchall()]
            conn.close()

            # Build JSON structure
            secrets_json = {}
            for server_name in servers:
                secrets_json[server_name] = self.get_server_secrets(server_name)

            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(secrets_json, f, indent=2)

            return True

        except Exception as e:
            print(f"Error exporting secrets: {e}")
            return False

    def import_from_json(self, input_path: Path) -> Tuple[int, int]:
        """
        Import secrets from JSON file (like secrets.json).

        Args:
            input_path: Path to JSON file with secrets

        Returns:
            Tuple of (successful_imports, failed_imports)
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                secrets_json = json.load(f)

            successful = 0
            failed = 0

            for server_name, credentials in secrets_json.items():
                # Skip special keys like _instructions
                if server_name.startswith('_'):
                    continue

                if not isinstance(credentials, dict):
                    continue

                for key_name, value in credentials.items():
                    if self.add_secret(server_name, key_name, str(value)):
                        successful += 1
                    else:
                        failed += 1

            return successful, failed

        except Exception as e:
            print(f"Error importing secrets: {e}")
            return 0, 0
