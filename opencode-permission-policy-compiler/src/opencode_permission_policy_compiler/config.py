from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import cast

import json5
from pydantic import validate_call

from .errors import ConfigError
from .models import ConfigDocument, PermissionFragmentData, PermissionRule, PolicyCatalogDocument

STANDARD_GLOBAL_CONFIG_PATH = Path.home() / ".config" / "opencode" / "opencode.json"
POLICY_CONFIG_DIRECTORY_NAME = "opencode-permission-policy-compiler"
POLICY_CONFIG_FILE_NAME = "config.toml"


@validate_call
def load_global_config_payload() -> dict[str, object]:
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

    return cast(dict[str, object], raw_payload)


@validate_call
def load_global_permission_base() -> dict[str, PermissionRule]:
    document = load_global_config_document()

    return document.resolved_permission()


@validate_call
def load_global_config_document() -> ConfigDocument:
    path = STANDARD_GLOBAL_CONFIG_PATH
    payload = load_global_config_payload()

    try:
        return ConfigDocument.model_validate(payload)
    except ValueError as exc:
        msg = f"Invalid permission block in OpenCode config {path}: {exc}"
        raise ConfigError(msg) from exc


@validate_call
def write_global_permission_base(permission: dict[str, PermissionRule]) -> Path:
    path = STANDARD_GLOBAL_CONFIG_PATH
    payload = load_global_config_payload()
    payload["permission"] = permission
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def policy_config_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    config_root = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
    return config_root / POLICY_CONFIG_DIRECTORY_NAME / POLICY_CONFIG_FILE_NAME


@validate_call
def load_policy_catalog_document() -> PolicyCatalogDocument:
    path = policy_config_path()
    if not path.is_file():
        msg = f"Global policy config does not exist: {path}"
        raise ConfigError(msg)

    try:
        raw_payload = cast(
            object,
            tomllib.loads(path.read_text(encoding="utf-8")),
        )
    except (OSError, tomllib.TOMLDecodeError) as exc:
        msg = f"Failed to parse global policy config {path}: {exc}"
        raise ConfigError(msg) from exc

    if not isinstance(raw_payload, dict):
        msg = f"Global policy config must be a TOML table: {path}"
        raise ConfigError(msg)
    payload = cast(dict[str, object], raw_payload)

    try:
        return PolicyCatalogDocument.model_validate(payload)
    except ValueError as exc:
        msg = f"Invalid global policy config {path}: {exc}"
        raise ConfigError(msg) from exc


@validate_call
def load_known_policies() -> dict[str, PermissionFragmentData]:
    return load_policy_catalog_document().resolved_policies()


@validate_call
def write_policy_config_text(content: str, *, overwrite: bool = False) -> Path:
    path = policy_config_path()
    if path.exists() and not overwrite:
        msg = f"Global policy config already exists: {path}"
        raise ConfigError(msg)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
