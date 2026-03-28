from __future__ import annotations

from pathlib import Path
from typing import cast

import json5
from pydantic import validate_call

from .errors import ConfigError
from .models import ConfigDocument, PermissionRule

STANDARD_GLOBAL_CONFIG_PATH = Path.home() / ".config" / "opencode" / "opencode.json"


@validate_call
def load_global_permission_base() -> dict[str, PermissionRule]:
    path = STANDARD_GLOBAL_CONFIG_PATH
    if not path.is_file():
        msg = f"Standard OpenCode global config does not exist: {path}"
        raise ConfigError(msg)

    try:
        raw_payload = cast(object, json5.loads(path.read_text(encoding="utf-8")))
    except ValueError as exc:
        msg = f"Failed to parse OpenCode config {path}: {exc}"
        raise ConfigError(msg) from exc

    if not isinstance(raw_payload, dict):
        msg = f"OpenCode config must be a JSON object: {path}"
        raise ConfigError(msg)
    payload = cast(dict[str, object], raw_payload)

    try:
        document = ConfigDocument.model_validate(payload)
    except ValueError as exc:
        msg = f"Invalid permission block in OpenCode config {path}: {exc}"
        raise ConfigError(msg) from exc

    return document.resolved_permission()
