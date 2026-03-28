from __future__ import annotations

from copy import deepcopy
from typing import cast

from pydantic import validate_call

from .errors import MarkdownError, PolicyResolutionError
from .markdown import parse_markdown_document, render_markdown_document
from .models import PermissionAction, PermissionRule

KNOWN_POLICIES: dict[str, dict[str, PermissionRule]] = {
    "review": {
        "edit": "deny",
        "webfetch": "deny",
        "websearch": "deny",
    },
    "git-inspect": {
        "bash": {
            "*": "ask",
            "git diff *": "allow",
            "git log *": "allow",
            "git status *": "allow",
        },
    },
    "no-web": {
        "webfetch": "deny",
        "websearch": "deny",
    },
    "bash-unrestricted": {
        "bash": "allow",
    },
}


@validate_call
def merge_permission_maps(*fragments: dict[str, PermissionRule]) -> dict[str, PermissionRule]:
    merged: dict[str, PermissionRule] = {}
    for fragment in fragments:
        for key, value in fragment.items():
            existing = merged.get(key)
            if isinstance(existing, dict) and isinstance(value, dict):
                merged_rules: dict[str, PermissionAction] = dict(existing)
                merged_rules.update(value)
                merged[key] = merged_rules
                continue
            merged[key] = deepcopy(value)
    return merged


@validate_call
def resolve_policy_permissions(
    policy_names: list[str],
    base_permissions: dict[str, PermissionRule],
) -> dict[str, PermissionRule]:
    layers: list[dict[str, PermissionRule]] = [base_permissions]
    available = sorted(KNOWN_POLICIES)
    for policy_name in policy_names:
        fragment = KNOWN_POLICIES.get(policy_name)
        if fragment is None:
            msg = f"Unknown policy {policy_name!r}. Valid policies: {available}"
            raise PolicyResolutionError(msg)
        layers.append(deepcopy(fragment))
    return merge_permission_maps(*layers)


@validate_call
def compute_minimal_permission_overlay(
    effective: dict[str, PermissionRule],
    base_permissions: dict[str, PermissionRule],
) -> dict[str, PermissionRule]:
    minimal: dict[str, PermissionRule] = {}
    for key, value in effective.items():
        delta = _compute_permission_delta(key, value, base_permissions)
        if delta is not None:
            minimal[key] = delta

    return minimal


def _compute_permission_delta(
    key: str,
    value: PermissionRule,
    base_permissions: dict[str, PermissionRule],
) -> PermissionRule | None:
    if key not in base_permissions:
        return deepcopy(value)

    base_value = base_permissions[key]
    if value == base_value:
        return None

    if isinstance(value, dict) and isinstance(base_value, dict):
        delta = _compute_rule_map_delta(value, base_value)
        return delta or None

    return deepcopy(value)


def _compute_rule_map_delta(
    value: dict[str, PermissionAction],
    base_value: dict[str, PermissionAction],
) -> dict[str, PermissionAction]:
    delta: dict[str, PermissionAction] = {}
    for inner_key, inner_value in value.items():
        if inner_key not in base_value or base_value[inner_key] != inner_value:
            delta[inner_key] = inner_value
    return delta


@validate_call
def compile_markdown_agent(
    markdown_text: str,
    base_permissions: dict[str, PermissionRule],
) -> str:
    metadata, body = parse_markdown_document(markdown_text)
    if "permission" in metadata:
        msg = "Input agent already contains a permission field; expected policies-only input"
        raise MarkdownError(msg)

    policy_names = _extract_policy_names(metadata.get("policies"))
    effective = resolve_policy_permissions(policy_names, base_permissions)
    minimal = compute_minimal_permission_overlay(effective, base_permissions)
    output_metadata = _build_output_metadata(metadata, minimal)
    return render_markdown_document(output_metadata, body)


def _extract_policy_names(raw_policies: object) -> list[str]:
    if not isinstance(raw_policies, list):
        msg = "Markdown frontmatter must contain policies as a list of policy names"
        raise MarkdownError(msg)

    policy_names: list[str] = []
    for item in cast(list[object], raw_policies):
        if not isinstance(item, str):
            msg = "Markdown frontmatter must contain policies as a list of policy names"
            raise MarkdownError(msg)
        policy_names.append(item)
    return policy_names


def _build_output_metadata(
    metadata: dict[str, object],
    minimal: dict[str, PermissionRule],
) -> dict[str, object]:
    output_metadata = {
        key: deepcopy(value)
        for key, value in metadata.items()
        if key not in {"policies", "permission"}
    }
    if minimal:
        output_metadata["permission"] = minimal
    return output_metadata
