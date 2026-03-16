"""Improved Jules CLI - Configuration."""

import os
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "improved-jules-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"


class ConfigError(Exception):
    """Configuration error."""

    pass


def ensure_config_dir():
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load config from file."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text())
    except json.JSONDecodeError:
        return {}


def save_config(config: dict):
    """Save config to file."""
    ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_api_key() -> str:
    """Get API key from config or env var."""
    # Check env var first
    env_key = os.environ.get("JULES_API_KEY")
    if env_key:
        return env_key

    # Check config file
    config = load_config()
    if config.get("api_key"):
        return config["api_key"]

    raise ConfigError(
        "No API key found. Set JULES_API_KEY env var or run: jules-cli config-set-api-key <key>"
    )


def set_api_key(key: str):
    """Save API key to config."""
    config = load_config()
    config["api_key"] = key
    save_config(config)
