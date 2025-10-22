"""
Key management for secrets encryption using machine-specific identifiers
"""
import os
import platform
import hashlib
from pathlib import Path
from typing import Optional
from .encryption import derive_key_from_password


class KeyManager:
    """Manages encryption keys for secrets storage"""

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize key manager.

        Args:
            data_dir: Directory to store key material (defaults to project data/)
        """
        if data_dir is None:
            # Default to project root data/ directory
            project_root = Path(__file__).resolve().parents[2]
            data_dir = project_root / 'data'

        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Path to store salt for key derivation
        self.salt_path = self.data_dir / '.key_salt'

    def get_machine_identifier(self) -> str:
        """
        Generate a machine-specific identifier.

        Uses multiple system properties to create a stable but unique identifier.

        Returns:
            Machine identifier string
        """
        # Collect machine-specific information
        components = [
            platform.node(),  # hostname
            platform.system(),  # OS name
            platform.machine(),  # architecture
        ]

        # Try to get more stable identifiers
        try:
            # On Windows, try to get machine GUID
            if platform.system() == 'Windows':
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Cryptography",
                    0,
                    winreg.KEY_READ | winreg.KEY_WOW64_64KEY
                )
                machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
                winreg.CloseKey(key)
                components.append(machine_guid)
        except Exception:
            # Fall back to hostname if registry access fails
            pass

        # Create hash of all components
        identifier = hashlib.sha256('|'.join(components).encode()).hexdigest()
        return identifier

    def get_or_create_salt(self) -> bytes:
        """
        Get existing salt or create new one.

        Returns:
            32-byte salt for key derivation
        """
        if self.salt_path.exists():
            with open(self.salt_path, 'rb') as f:
                salt = f.read()
            if len(salt) == 32:
                return salt

        # Generate new salt
        salt = os.urandom(32)
        with open(self.salt_path, 'wb') as f:
            f.write(salt)

        # Make salt file read-only (best effort)
        try:
            os.chmod(self.salt_path, 0o400)
        except Exception:
            pass

        return salt

    def get_master_key(self) -> bytes:
        """
        Get or generate the master encryption key.

        Key is derived from machine identifier + random salt using PBKDF2.

        Returns:
            32-byte master encryption key
        """
        machine_id = self.get_machine_identifier()
        salt = self.get_or_create_salt()

        # Derive key using PBKDF2 with 100k iterations
        master_key = derive_key_from_password(machine_id, salt, iterations=100000)

        return master_key

    def rotate_key(self) -> bytes:
        """
        Rotate the master encryption key.

        WARNING: This requires re-encrypting all existing secrets.

        Returns:
            New 32-byte master encryption key
        """
        # Remove old salt to force new key generation
        if self.salt_path.exists():
            self.salt_path.unlink()

        # Generate new key
        return self.get_master_key()
