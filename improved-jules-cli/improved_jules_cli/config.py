"""Improved Jules CLI - Configuration."""

import os
import json
import subprocess
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
    """Get prompt template from config or from ai-prompts."""
    config = load_config()

    # Check for ai-prompts slug
    prompt_slug = config.get("prompt_slug")
    if prompt_slug:
        try:
            result = subprocess.run(
                ["uvx", "ai-prompts", "get", prompt_slug],
                capture_output=True,
                text=True,
                cwd=os.environ.get(
                    "AI_PROMPTS_DIR", "/home/dzack/opencode-plugins/ai-prompts"
                ),
                env={**os.environ, "PROMPTS_DIR": "prompts"},
            )
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass

    # Fallback to file path
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


def set_prompt_slug(slug: str):
    """Set ai-prompts slug for prompt template."""
    config = load_config()
    config["prompt_slug"] = slug
    save_config(config)
