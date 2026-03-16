"""Improved Jules CLI - Configuration."""

import json
import os
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".config" / "improved-jules-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Default ai-prompts directory
AI_PROMPTS_DIR = os.environ.get(
    "AI_PROMPTS_DIR", "/home/dzack/opencode-plugins/ai-prompts"
)


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


def get_prompt_template(task: str) -> Optional[str]:
    """Get prompt template and render with task binding via templating engine."""
    config = load_config()

    # Check for ai-prompts slug
    prompt_slug = config.get("prompt_slug")
    if prompt_slug:
        return _render_template_from_slug(prompt_slug, task)

    # Fallback to file path
    template_path = config.get("prompt_template_path")
    if not template_path:
        return None

    path = Path(template_path)
    if not path.exists():
        raise ConfigError(f"Prompt template not found: {template_path}")

    # Render file as template with task
    template = path.read_text()
    return template.replace("{{ task }}", task).replace("{{task}}", task)


def _render_template_from_slug(slug: str, task: str) -> str:
    """Render template from ai-prompts slug using simple string replacement."""
    import sys

    # Add ai-prompts to path for imports
    ai_prompts_path = Path(AI_PROMPTS_DIR)
    if str(ai_prompts_path / "src") not in sys.path:
        sys.path.insert(0, str(ai_prompts_path / "src"))

    # Set PROMPTS_DIR for ai_prompts catalog
    original_prompts_dir = os.environ.get("PROMPTS_DIR")
    os.environ["PROMPTS_DIR"] = str(ai_prompts_path / "prompts")

    try:
        from ai_prompts.catalog import get_prompt

        prompt = get_prompt(slug)
        # Use simple string replacement for {{ task }} placeholder
        return prompt.text.replace("{{ task }}", task).replace("{{task}}", task)
    except Exception:
        # Fallback: just return task
        return task
    finally:
        # Restore original PROMPTS_DIR
        if original_prompts_dir is None:
            os.environ.pop("PROMPTS_DIR", None)
        else:
            os.environ["PROMPTS_DIR"] = original_prompts_dir


def set_prompt_template_path(path: str):
    config = load_config()
    config["prompt_template_path"] = path
    save_config(config)


def set_prompt_slug(slug: str):
    """Set ai-prompts slug for prompt template."""
    config = load_config()
    config["prompt_slug"] = slug
    save_config(config)
