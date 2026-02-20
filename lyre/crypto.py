"""Credential encryption utilities for Lyre.

Uses Fernet symmetric encryption (from the `cryptography` package) to
protect sensitive values (API tokens, secrets) stored in the config file.

Encrypted values are prefixed with ``ENC:`` so the loader can detect and
decrypt them transparently at startup.  The encryption key is stored in a
separate file (``CONFIG_DIR/.lyre.key``) which is **not** the config file
itself, adding a layer of separation.
"""

import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet

from lyre.logger import logger


# Sentinel prefix that marks a value as encrypted
_ENC_PREFIX = "ENC:"

# Fields in the config that should be encrypted
SENSITIVE_FIELDS = frozenset({
    "MISSKEY_TOKEN",
    "LASTFM_API_KEY",
    "LASTFM_API_SECRET",
})


def _key_path() -> Path:
    """Return the path to the encryption key file."""
    from lyre.config import CONFIG_DIR
    return CONFIG_DIR / ".lyre.key"


def generate_key() -> bytes:
    """Generate a new Fernet key and persist it to disk.

    If the key file already exists it is **not** overwritten.
    Returns the key bytes in both cases.
    """
    path = _key_path()
    if path.exists():
        return path.read_bytes().strip()

    key = Fernet.generate_key()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key)
    # Restrict permissions on Unix (best-effort, ignored on Windows)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    logger.debug(f"Encryption key generated at {path}")
    return key


def load_key() -> bytes:
    """Load the Fernet key from disk, generating one if it does not exist."""
    path = _key_path()
    if not path.exists():
        return generate_key()
    return path.read_bytes().strip()


def encrypt_value(plain: str) -> str:
    """Encrypt a plaintext string and return an ``ENC:``-prefixed token."""
    key = load_key()
    f = Fernet(key)
    token = f.encrypt(plain.encode("utf-8"))
    return f"{_ENC_PREFIX}{token.decode('utf-8')}"


def decrypt_value(token: str) -> str:
    """Decrypt an ``ENC:``-prefixed token back to plaintext.

    If the value is not prefixed with ``ENC:`` it is returned as-is
    (i.e. plaintext values pass through unchanged).
    """
    if not is_encrypted(token):
        return token
    key = load_key()
    f = Fernet(key)
    raw = token[len(_ENC_PREFIX):]
    return f.decrypt(raw.encode("utf-8")).decode("utf-8")


def is_encrypted(value: str) -> bool:
    """Return True if *value* carries the ``ENC:`` prefix."""
    return value.startswith(_ENC_PREFIX)


def encrypt_config_file(config_path: Path) -> None:
    """Re-encrypt sensitive fields in an existing config file in-place.

    Non-sensitive lines and already-encrypted values are left untouched.
    """
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}")
        return

    lines = config_path.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    changed = 0

    for line in lines:
        stripped = line.strip()
        # Skip comments and empty lines
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        if "=" in stripped:
            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip()

            if key in SENSITIVE_FIELDS and value and not is_encrypted(value):
                encrypted = encrypt_value(value)
                new_lines.append(f"{key}={encrypted}")
                changed += 1
                continue

        new_lines.append(line)

    config_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    logger.info(f"Encrypted {changed} sensitive field(s) in {config_path}")
