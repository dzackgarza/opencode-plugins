"""Improved Jules CLI - Configuration."""

import os
from pathlib import Path
from typing import Optional

# Default ai-prompts directory
AI_PROMPTS_DIR = os.environ.get(
    "AI_PROMPTS_DIR", "/home/dzack/opencode-plugins/ai-prompts"
)


class ConfigError(Exception):
    pass


def get_api_key() -> str:
    """Get API key from environment. Fails if not set."""
    env_key = os.environ.get("JULES_API_KEY")
    if env_key:
        return env_key

    raise ConfigError("JULES_API_KEY environment variable is required")


def get_prompt_template(
    task: str,
    context_files: Optional[list[str]] = None,
    prompt_slug: Optional[str] = None,
    template_path: Optional[str] = None,
) -> Optional[str]:
    """Get prompt template and render with task binding via templating engine.

    Args:
        task: The task/issue to render in the template
        context_files: List of file paths to include as text_files bindings
        prompt_slug: ai-prompts slug (e.g., "sub-agents/jules-pr-body-contract")
        template_path: Path to template file
    """

    # Check for ai-prompts slug
    if prompt_slug:
        return _render_template_from_slug(prompt_slug, task, context_files)

    # Fallback to file path
    if not template_path:
        return None

    path = Path(template_path)
    if not path.exists():
        raise ConfigError(f"Prompt template not found: {template_path}")

    # Render file as template with task
    template = path.read_text()
    return template.replace("{{ task }}", task).replace("{{task}}", task)


def _render_template_from_slug(
    slug: str,
    task: str,
    context_files: Optional[list[str]] = None,
) -> str:
    """Render template from ai-prompts slug using templating engine CLI via uvx."""
    import json
    import subprocess

    # Build bindings with additional_context for extra files
    bindings = {"data": {"task": task, "additional_context": []}, "text_files": []}

    if context_files:
        # Read files and format as list of {name, content}
        context_list = []
        for filepath in context_files:
            try:
                content = Path(filepath).read_text()
                name = Path(filepath).name  # basename only
                context_list.append({"name": name, "content": content})
            except Exception:
                pass
        if context_list:
            bindings["data"]["additional_context"] = context_list

    request = {
        "template": {"path": f"prompts/{slug}.md"},
        "bindings": bindings,
        "options": {"render_mode": "document"},
    }

    try:
        # Use uvx to run the templating engine
        result = subprocess.run(
            [
                "uvx",
                "--from",
                "git+https://github.com/dzackgarza/llm-templating-engine.git",
                "llm-template-render",
            ],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            cwd=AI_PROMPTS_DIR,
            env={**os.environ, "PROMPTS_DIR": "prompts"},
        )
        if result.returncode == 0:
            response = json.loads(result.stdout)
            return response.get("rendered", {}).get("body", "")
    except Exception:
        pass

    # Fallback: just return task
    return task
