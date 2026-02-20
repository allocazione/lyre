"""Configuration loader and first-run interactive setup.

Loads settings from a config file stored in a platform-specific directory:
  - Linux/macOS: ~/.config/lyre/config.env
  - Windows:     %USERPROFILE%\\.lyre\\config.env

If no config file exists, runs first_exec() to interactively prompt the
user for all required settings and writes the file automatically.

Configuration is NOT loaded automatically on import. Call
init_config() explicitly after parsing CLI arguments so that
debug flags can bypass the interactive wizard.
"""

import os
import re
import sys
import platform
from pathlib import Path
from dotenv import load_dotenv


def _normalize_fedi_account(value: str) -> str:
    """Normalize and validate a Fediverse handle.

    Accepts formats like ``@user@instance``, ``user@instance``, or blank.
    Returns ``@user@instance`` on success, or an empty string if the
    value is blank or malformed.
    """
    value = value.strip()
    if not value:
        return ""
    # Ensure leading '@'
    if not value.startswith("@"):
        value = "@" + value
    # Basic format check: @user@domain (domain must have at least one dot)
    if re.match(r"^@[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}$", value):
        return value
    return ""


def _get_config_dir() -> Path:
    """Return the platform-specific configuration directory for Lyre.

    - Linux/macOS: ~/.config/lyre/
    - Windows:     ~/.lyre/
    """
    if platform.system() == "Windows":
        return Path.home() / ".lyre"
    else:
        # Follow XDG Base Directory Specification on Linux/macOS.
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "lyre"
        return Path.home() / ".config" / "lyre"


CONFIG_DIR = _get_config_dir()
CONFIG_FILE = CONFIG_DIR / "config.env"


def first_exec():
    """Interactive first-run setup.

    Prompts the user for all required configuration values and writes
    them to the config file. Called automatically when no config is found.
    """
    try:
        _first_exec_inner()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(0)


def _first_exec_inner():
    """The actual setup logic, separated so KeyboardInterrupt is caught cleanly."""
    print("=" * 60)
    print("  Lyre -- First Run Setup")
    print("=" * 60)
    print()
    print(f"No configuration file was found.")
    print(f"Config will be saved to: {CONFIG_FILE}")
    print("This wizard will help you set up the bot.\n")

    # -- Misskey / Mastodon ---------------------------------------------------
    print("--- Misskey / Mastodon Configuration ---\n")

    instance_url = ""
    while not instance_url.strip():
        instance_url = input("Instance URL (e.g. https://misskey.io): ").strip()
        if not instance_url:
            print("  This field is required.\n")

    token = ""
    while not token.strip():
        token = input("API Access Token: ").strip()
        if not token:
            print("  This field is required.\n")

    # -- Music Provider -------------------------------------------------------
    print("\n--- Music Provider ---\n")
    print("Supported providers:")
    print("  1) Last.fm")
    print("  2) Stats.fm")
    print()

    provider_choice = ""
    while provider_choice not in ("1", "2"):
        provider_choice = input("Choose a provider [1/2]: ").strip()

    provider = "lastfm" if provider_choice == "1" else "statsfm"

    lastfm_key = ""
    lastfm_secret = ""
    lastfm_user = ""
    statsfm_user = ""

    if provider == "lastfm":
        print("\n--- Last.fm Configuration ---\n")
        print("Get your API key at: https://www.last.fm/api/account/create\n")

        while not lastfm_key.strip():
            lastfm_key = input("Last.fm API Key: ").strip()
            if not lastfm_key:
                print("  This field is required.\n")

        while not lastfm_secret.strip():
            lastfm_secret = input("Last.fm API Secret: ").strip()
            if not lastfm_secret:
                print("  This field is required.\n")

        while not lastfm_user.strip():
            lastfm_user = input("Last.fm Username: ").strip()
            if not lastfm_user:
                print("  This field is required.\n")
    else:
        print("\n--- Stats.fm Configuration ---\n")
        while not statsfm_user.strip():
            statsfm_user = input("Stats.fm Username: ").strip()
            if not statsfm_user:
                print("  This field is required.\n")

    # -- Fediverse Account ----------------------------------------------------
    print("\n--- Fediverse Account ---\n")
    print("Optionally link your own Fediverse account so the bot mentions")
    print("you in every 'now listening' note (e.g. @user@instance.social).\n")

    raw_fedi = input("Your Fediverse handle (leave blank to skip): ").strip()
    fedi_account = _normalize_fedi_account(raw_fedi)
    if raw_fedi and not fedi_account:
        print("  Invalid handle format. Expected @user@instance.tld — skipping.")

    # -- Bot Settings ---------------------------------------------------------
    print("\n--- Bot Settings ---\n")

    post_notes_input = input("Post notes when track changes? [Y/n]: ").strip().lower()
    post_notes = "false" if post_notes_input == "n" else "true"

    poll_input = input("Polling interval in seconds [30]: ").strip()
    poll_interval = poll_input if poll_input.isdigit() and int(poll_input) > 0 else "30"

    # -- Write config ---------------------------------------------------------
    # Encrypt sensitive fields before writing to disk
    from lyre.crypto import encrypt_value, SENSITIVE_FIELDS, generate_key
    generate_key()  # Ensure encryption key exists

    def _enc(field_name: str, value: str) -> str:
        if field_name in SENSITIVE_FIELDS and value:
            return encrypt_value(value)
        return value

    lines = [
        "# Lyre Configuration (auto-generated by first-run setup)",
        "# Sensitive values are encrypted with ENC: prefix.",
        "",
        "# -- Misskey / Mastodon --",
        f"MISSKEY_INSTANCE_URL={instance_url}",
        f"MISSKEY_TOKEN={_enc('MISSKEY_TOKEN', token)}",
        "",
        "# -- Music Provider --",
        f"MUSIC_PROVIDER={provider}",
        "",
        "# -- Last.fm --",
        f"LASTFM_API_KEY={_enc('LASTFM_API_KEY', lastfm_key)}",
        f"LASTFM_API_SECRET={_enc('LASTFM_API_SECRET', lastfm_secret)}",
        f"LASTFM_USERNAME={lastfm_user}",
        "",
        "# -- Stats.fm --",
        f"STATSFM_USERNAME={statsfm_user}",
        "",
        "# -- Fediverse Account --",
        f"FEDI_ACCOUNT={fedi_account}",
        "",
        "# -- Bot Settings --",
        f"POST_NOTES={post_notes}",
        f"POLL_INTERVAL={poll_interval}",
    ]

    # Create the config directory if it does not exist
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print()
    print(f"Configuration saved to: {CONFIG_FILE}")
    print("You can edit this file at any time to change your settings.")
    print("=" * 60)
    print()


_config_loaded = False


def init_config(skip_wizard: bool = False):
    """Load configuration from disk.

    Args:
        skip_wizard: If True, skip the interactive first_exec() wizard
                     even when no config file exists.  Used by debug
                     flags that only need whatever env vars are already set.
    """
    global _config_loaded
    if _config_loaded:
        return

    if CONFIG_FILE.exists():
        load_dotenv(CONFIG_FILE)
    elif not skip_wizard:
        first_exec()
        load_dotenv(CONFIG_FILE)
    # else: no config file and wizard skipped -- rely on env vars only

    Config.reload()
    _config_loaded = True


class Config:
    """Application configuration loaded from environment variables."""

    # Path where the config file lives (exposed for other modules / README)
    CONFIG_DIR: Path = CONFIG_DIR
    CONFIG_FILE: Path = CONFIG_FILE

    # Misskey / Mastodon
    MISSKEY_INSTANCE_URL: str = os.getenv("MISSKEY_INSTANCE_URL", "")
    MISSKEY_TOKEN: str = os.getenv("MISSKEY_TOKEN", "")

    # Music Provider
    MUSIC_PROVIDER: str = os.getenv("MUSIC_PROVIDER", "lastfm").lower()

    # Last.fm
    LASTFM_API_KEY: str = os.getenv("LASTFM_API_KEY", "")
    LASTFM_API_SECRET: str = os.getenv("LASTFM_API_SECRET", "")
    LASTFM_USERNAME: str = os.getenv("LASTFM_USERNAME", "")

    # Stats.fm
    STATSFM_USERNAME: str = os.getenv("STATSFM_USERNAME", "")

    # Fediverse Account (optional mention tag in posted notes)
    FEDI_ACCOUNT: str = _normalize_fedi_account(os.getenv("FEDI_ACCOUNT", ""))

    # Feature Flags
    POST_NOTES: bool = os.getenv("POST_NOTES", "true").lower() == "true"
    POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", "30"))

    @classmethod
    def reload(cls):
        """Reload configuration from the config file.

        Transparently decrypts any ``ENC:``-prefixed values.
        """
        load_dotenv(CONFIG_FILE, override=True)

        def _dec(key: str, default: str = "") -> str:
            """Get an env var and decrypt it if it carries the ENC: prefix."""
            value = os.getenv(key, default)
            try:
                from lyre.crypto import decrypt_value
                return decrypt_value(value)
            except Exception as e:
                from lyre.logger import logger
                logger.error(f"Failed to decrypt config field '{key}': {e}. Check if .lyre.key is valid.")
                return value

        cls.MISSKEY_INSTANCE_URL = os.getenv("MISSKEY_INSTANCE_URL", "")
        cls.MISSKEY_TOKEN = _dec("MISSKEY_TOKEN")
        cls.MUSIC_PROVIDER = os.getenv("MUSIC_PROVIDER", "lastfm").lower()
        cls.LASTFM_API_KEY = _dec("LASTFM_API_KEY")
        cls.LASTFM_API_SECRET = _dec("LASTFM_API_SECRET")
        cls.LASTFM_USERNAME = os.getenv("LASTFM_USERNAME", "")
        cls.STATSFM_USERNAME = os.getenv("STATSFM_USERNAME", "")
        cls.FEDI_ACCOUNT = _normalize_fedi_account(os.getenv("FEDI_ACCOUNT", ""))
        cls.POST_NOTES = os.getenv("POST_NOTES", "true").lower() == "true"
        cls.POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))

    @classmethod
    def validate(cls):
        """Validate that all required configuration values are present."""
        if not cls.MISSKEY_INSTANCE_URL or not cls.MISSKEY_TOKEN:
            raise ValueError(
                "Missing Misskey configuration. "
                f"Set MISSKEY_INSTANCE_URL and MISSKEY_TOKEN in {CONFIG_FILE}"
            )

        if cls.MUSIC_PROVIDER == "lastfm":
            if not cls.LASTFM_API_KEY or not cls.LASTFM_API_SECRET or not cls.LASTFM_USERNAME:
                raise ValueError(
                    "Missing Last.fm configuration. "
                    "Set LASTFM_API_KEY, LASTFM_API_SECRET, and LASTFM_USERNAME."
                )
        elif cls.MUSIC_PROVIDER == "statsfm":
            if not cls.STATSFM_USERNAME:
                raise ValueError(
                    "Missing Stats.fm configuration. Set STATSFM_USERNAME."
                )
        else:
            raise ValueError(
                f"Unknown music provider: '{cls.MUSIC_PROVIDER}'. "
                "Use 'lastfm' or 'statsfm'."
            )

        # Soft warning for malformed FEDI_ACCOUNT (non-fatal)
        raw_fedi = os.getenv("FEDI_ACCOUNT", "")
        if raw_fedi and not cls.FEDI_ACCOUNT:
            import warnings
            warnings.warn(
                f"FEDI_ACCOUNT value '{raw_fedi}' looks malformed "
                f"(expected @user@instance.tld). Notes will not include a mention."
            )
