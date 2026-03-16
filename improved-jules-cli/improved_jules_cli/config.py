"""Improved Jules CLI - Configuration."""

import os
import json
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".config" / "improved-jules-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"


class ConfigError(Exception):
    pass


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text())
    except json.JSONDecodeError:
        return {}


def save_config(config: dict):
    ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_api_key() -> str:
    env_key = os.environ.get("JULES_API_KEY")
    if env_key:
        return env_key

    config = load_config()
    if config.get("api_key"):
        return config["api_key"]

    raise ConfigError("Set JULES_API_KEY or run: jules-cli config-set-api-key <key>")


def set_api_key(key: str):
    config = load_config()
    config["api_key"] = key
    save_config(config)


def get_prompt_template() -> Optional[str]:
    config = load_config()
    template_path = config.get("prompt_template_path")
    if not template_path:
        return None

    path = Path(template_path)
    if not path.exists():
        raise ConfigError(f"Prompt template not found: {template_path}")

    return path.read_text()


def set_prompt_template_path(path: str):
    config = load_config()
    config["prompt_template_path"] = path
    save_config(config)
