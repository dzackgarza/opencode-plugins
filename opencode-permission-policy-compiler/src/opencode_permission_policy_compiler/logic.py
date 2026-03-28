from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from copy import deepcopy
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import mcp2cli
from pydantic import TypeAdapter, ValidationError, validate_call

from .errors import ConfigError, MarkdownError, PolicyResolutionError
from .markdown import parse_markdown_document, render_markdown_document
from .models import (
    DoctorInputDocument,
    DoctorReportDocument,
    McpDisabledServerDocument,
    McpLocalServerDocument,
    McpRemoteServerDocument,
    NonToolPermissionStatus,
    PermissionAction,
    PermissionFragmentData,
    PermissionMismatchStatus,
    PermissionRule,
    ServerHealthDocument,
    ServerStatusDocument,
    ToolIDsDocument,
    ToolPermissionStatus,
)

DEFAULT_SERVER_BASE_URLS = ("http://127.0.0.1:4096", "http://localhost:4096")
GLOBAL_POLICY_NAME = "global"
SUBAGENTS_POLICY_NAME = "subagents"
NON_TOOL_PERMISSION_KEYS = ("external_directory", "doom_loop")
NON_TOOL_PERMISSION_DEFAULTS: dict[str, PermissionAction] = {
    "external_directory": "ask",
    "doom_loop": "ask",
}
GLOBAL_PERMISSION_DEFAULT_KEY = "*"
SUBAGENTS_POLICY_LINES = (
    'task = "deny"',
    'question = "deny"',
    'submit_plan = "deny"',
    'plannotator_review = "deny"',
    'plannotator_annotate = "deny"',
)
COMMENTED_GLOBAL_POLICY_GUIDANCE = (
    "# Replace a scalar permission with a table like the examples below when you need",
    "# path-, glob-, or command-specific matching rules.",
    "# [policies.global.read]",
    '# "*" = "allow"',
    '# "*.env" = "deny"',
    '# "*.env.*" = "deny"',
    '# "*.env.example" = "allow"',
    "",
    "# [policies.global.edit]",
    '# "*" = "allow"',
    '# "/path/to/trusted/project/docs/**" = "deny"',
    "",
    "# [policies.global.bash]",
    '# "*" = "allow"',
    '# "git *" = "allow"',
    '# "rm *" = "deny"',
    "",
    "# [policies.global.external_directory]",
    '# "*" = "ask"',
    '# "/path/to/trusted/root/**" = "allow"',
)
PERMISSION_FRAGMENT_ADAPTER = TypeAdapter(PermissionFragmentData)


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
    known_policies: dict[str, PermissionFragmentData],
    base_permissions: dict[str, PermissionRule],
) -> dict[str, PermissionRule]:
    layers: list[dict[str, PermissionRule]] = [base_permissions]
    available = sorted(known_policies)
    for policy_name in policy_names:
        fragment = known_policies.get(policy_name)
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
    known_policies: dict[str, PermissionFragmentData],
) -> str:
    metadata, body = parse_markdown_document(markdown_text)
    if "tools" in metadata:
        msg = "Input agent already contains a tools field; use permission instead"
        raise MarkdownError(msg)

    input_permissions = _extract_input_permissions(metadata.get("permission"))
    policy_names = _resolve_policy_names(metadata)
    effective = resolve_policy_permissions(
        policy_names,
        known_policies,
        merge_permission_maps(base_permissions, input_permissions),
    )
    minimal = compute_minimal_permission_overlay(effective, base_permissions)
    output_metadata = _build_output_metadata(metadata, minimal)
    return render_markdown_document(output_metadata, body)


def _resolve_policy_names(metadata: dict[str, object]) -> list[str]:
    policy_names = _extract_explicit_policy_names(metadata.get("policies"))
    if metadata.get("mode") != "subagent":
        return policy_names

    if SUBAGENTS_POLICY_NAME not in policy_names:
        policy_names.append(SUBAGENTS_POLICY_NAME)
    return policy_names


def _extract_explicit_policy_names(raw_policies: object) -> list[str]:
    if raw_policies is None:
        return []
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


def _extract_input_permissions(raw_permission: object) -> dict[str, PermissionRule]:
    if raw_permission is None:
        return {}
    try:
        permission_fragment = PERMISSION_FRAGMENT_ADAPTER.validate_python(raw_permission)
    except ValidationError as exc:
        msg = f"Markdown frontmatter permission field is invalid: {exc}"
        raise MarkdownError(msg) from exc
    return {key: deepcopy(value) for key, value in permission_fragment.items()}


def _build_output_metadata(
    metadata: dict[str, object],
    minimal: dict[str, PermissionRule],
) -> dict[str, object]:
    preferred_order = ("name", "model", "mode", "description")
    filtered_metadata = {
        key: deepcopy(value)
        for key, value in metadata.items()
        if key not in {"policies", "permission", "tools"}
    }
    output_metadata: dict[str, object] = {}
    for key in preferred_order:
        if key in filtered_metadata:
            output_metadata[key] = filtered_metadata.pop(key)
    if minimal:
        output_metadata["permission"] = minimal
    for key, value in filtered_metadata.items():
        output_metadata[key] = value
    return output_metadata


@validate_call
def build_doctor_report(
    inputs: DoctorInputDocument,
) -> DoctorReportDocument:
    server_status = _detect_server(inputs.server_base_urls)
    tool_permissions, tool_scan_error, inactive_configured_permissions = _tool_diagnostics(
        server_status=server_status,
        global_policy_permissions=inputs.global_policy_permissions,
        configured_mcp_servers=inputs.configured_mcp_servers,
        mcp_servers=inputs.mcp_servers,
    )
    policy_only_permissions, current_only_permissions, mismatched_permissions = (
        _global_policy_difference_statuses(
            current_permissions=inputs.current_permissions,
            global_policy_permissions=inputs.global_policy_permissions,
        )
    )
    global_policy_applied, global_policy_application_error = _global_policy_application_status(
        current_permissions=inputs.current_permissions,
        global_policy_permissions=inputs.global_policy_permissions,
        policy_config_error=inputs.policy_config_error,
        global_config_error=inputs.global_config_error,
    )

    return DoctorReportDocument(
        policy_config_path=inputs.policy_config_path,
        policy_config_valid=inputs.policy_config_error is None,
        policy_config_error=inputs.policy_config_error,
        global_config_path=inputs.global_config_path,
        global_config_valid=inputs.global_config_error is None,
        global_config_error=inputs.global_config_error,
        global_policy_applied=global_policy_applied,
        global_policy_application_error=global_policy_application_error,
        server=server_status,
        tool_permissions=tool_permissions,
        non_tool_permissions=_non_tool_permission_statuses(inputs.global_policy_permissions),
        policy_only_permissions=policy_only_permissions,
        current_only_permissions=current_only_permissions,
        mismatched_permissions=mismatched_permissions,
        tool_scan_error=tool_scan_error,
        inactive_configured_permissions=inactive_configured_permissions,
    )


@validate_call
def render_doctor_report(report: DoctorReportDocument) -> str:
    lines = [
        f"Policy config: {report.policy_config_path}",
        _status_line("schema", report.policy_config_valid, report.policy_config_error),
        f"OpenCode config target: {report.global_config_path}",
        "Global policy vs OpenCode permissions:",
        "  Doctor compares this CLI's policies.global against the live OpenCode",
        "  top-level permission block.",
        "  Guarantee: if this status is OK, the global CLI policy and the live",
        "  OpenCode permissions are identical.",
        _global_policy_application_line(report),
    ]

    lines.extend(_render_global_policy_difference_lines(report))
    lines.append(_render_server_line(report.server))
    lines.extend(_render_active_tool_lines(report))
    lines.extend(
        _render_non_tool_permission_lines(
            report.non_tool_permissions,
            report.tool_scan_error,
        )
    )
    lines.extend(
        _render_inactive_permission_lines(
            report.inactive_configured_permissions,
            report.tool_scan_error,
        )
    )

    return "\n".join(lines) + "\n"


@validate_call
def doctor_exit_code(report: DoctorReportDocument) -> int:
    return 1 if report.has_errors() else 0


def _global_policy_application_status(
    *,
    current_permissions: dict[str, PermissionRule] | None,
    global_policy_permissions: dict[str, PermissionRule] | None,
    policy_config_error: str | None,
    global_config_error: str | None,
) -> tuple[bool | None, str | None]:
    if policy_config_error is not None:
        return None, policy_config_error
    if global_config_error is not None:
        return None, global_config_error
    if global_policy_permissions is None:
        msg = f"CLI policy config must define [policies.{GLOBAL_POLICY_NAME}]"
        return None, msg
    if current_permissions is None:
        msg = "OpenCode global permission block is unavailable"
        return None, msg
    return current_permissions == global_policy_permissions, None


def _global_policy_difference_statuses(
    *,
    current_permissions: dict[str, PermissionRule] | None,
    global_policy_permissions: dict[str, PermissionRule] | None,
) -> tuple[list[str], list[str], list[PermissionMismatchStatus]]:
    if current_permissions is None or global_policy_permissions is None:
        return [], [], []

    policy_only_permissions = sorted(set(global_policy_permissions) - set(current_permissions))
    current_only_permissions = sorted(set(current_permissions) - set(global_policy_permissions))
    mismatched_permissions = [
        PermissionMismatchStatus(
            name=name,
            policy_value=deepcopy(global_policy_permissions[name]),
            current_value=deepcopy(current_permissions[name]),
        )
        for name in sorted(set(global_policy_permissions) & set(current_permissions))
        if global_policy_permissions[name] != current_permissions[name]
    ]
    return policy_only_permissions, current_only_permissions, mismatched_permissions


def _detect_server(server_base_urls: list[str]) -> ServerStatusDocument:
    candidates = _dedupe_urls([*server_base_urls, *DEFAULT_SERVER_BASE_URLS])
    for base_url in candidates:
        try:
            health = _fetch_server_health(base_url)
        except ConfigError:
            continue
        if not health.healthy:
            continue
        return ServerStatusDocument(
            running=True,
            base_url=base_url,
            version=health.version,
        )
    return ServerStatusDocument(running=False)


def _tool_diagnostics(
    *,
    server_status: ServerStatusDocument,
    global_policy_permissions: dict[str, PermissionRule] | None,
    configured_mcp_servers: list[str],
    mcp_servers: dict[
        str,
        McpLocalServerDocument | McpRemoteServerDocument | McpDisabledServerDocument,
    ]
    | None,
) -> tuple[list[ToolPermissionStatus], str | None, list[str]]:
    if not _server_can_list_tools(server_status):
        return [], None, []

    tool_ids, tool_scan_error = _discover_known_tool_ids(
        server_status=server_status,
        configured_mcp_servers=configured_mcp_servers,
        mcp_servers=mcp_servers,
    )
    if tool_scan_error is not None or tool_ids is None:
        return [], tool_scan_error, []

    if global_policy_permissions is None:
        msg = f"CLI policy config must define [policies.{GLOBAL_POLICY_NAME}]"
        return [], msg, []

    explicit_permissions = set(global_policy_permissions)
    return (
        _tool_permission_statuses(tool_ids, explicit_permissions),
        None,
        _inactive_configured_permissions(tool_ids, explicit_permissions),
    )


def _fetch_server_health(base_url: str) -> ServerHealthDocument:
    payload = _read_json(f"{base_url}/global/health")
    try:
        return ServerHealthDocument.model_validate(payload)
    except ValueError as exc:
        msg = f"Invalid server health response from {base_url}: {exc}"
        raise ConfigError(msg) from exc


def _fetch_tool_ids(base_url: str) -> list[str]:
    payload = _read_json(f"{base_url}/experimental/tool/ids")
    try:
        return ToolIDsDocument.model_validate(payload).root
    except ValueError as exc:
        msg = f"Invalid tool id response from {base_url}: {exc}"
        raise ConfigError(msg) from exc


def _read_json(url: str) -> object:
    try:
        with urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        msg = f"Failed to read {url}: {exc}"
        raise ConfigError(msg) from exc


def _dedupe_urls(urls: list[str]) -> list[str]:
    deduped: list[str] = []
    for url in urls:
        if url not in deduped:
            deduped.append(url)
    return deduped


def _checkbox(enabled: bool) -> str:
    return "[x]" if enabled else "[ ]"


def _status_line(label: str, ok: bool, detail: str | None) -> str:
    if ok:
        return f"  {label}: OK"
    return f"  {label}: ERROR {detail}"


def _global_policy_application_line(report: DoctorReportDocument) -> str:
    if report.global_policy_applied is True:
        return "  global policy reflected in OpenCode permissions: OK"
    if report.global_policy_applied is False:
        return (
            "  global policy reflected in OpenCode permissions: ERROR live OpenCode "
            "permissions do not match CLI policies.global"
        )
    return (
        "  global policy reflected in OpenCode permissions: unavailable "
        f"({report.global_policy_application_error})"
    )


def _render_global_policy_difference_lines(report: DoctorReportDocument) -> list[str]:
    if report.global_policy_applied is None:
        return []
    if report.global_policy_applied is True:
        return ["Global policy vs OpenCode permission differences:", "  none"]

    return [
        "Global policy vs OpenCode permission differences:",
        *_render_named_difference_section(
            heading="  Permissions in policies.global but not in OpenCode:",
            item_prefix="[policy-only-permission]",
            names=report.policy_only_permissions,
        ),
        *_render_named_difference_section(
            heading="  Permissions in OpenCode but not in policies.global:",
            item_prefix="[opencode-only-permission]",
            names=report.current_only_permissions,
        ),
        *_render_value_mismatch_section(report.mismatched_permissions),
    ]


def _render_named_difference_section(
    *,
    heading: str,
    item_prefix: str,
    names: list[str],
) -> list[str]:
    if not names:
        return [heading, "  none"]
    return [heading, *(f"  {item_prefix} {name}" for name in names)]


def _render_value_mismatch_section(
    mismatched_permissions: list[PermissionMismatchStatus],
) -> list[str]:
    if not mismatched_permissions:
        return ["  Permissions present in both but configured differently:", "  none"]

    lines = ["  Permissions present in both but configured differently:"]
    for mismatch in mismatched_permissions:
        lines.extend(
            [
                f"  [shared-permission-mismatch] {mismatch.name}",
                f"    policies.global: {_render_permission_rule(mismatch.policy_value)}",
                f"    opencode.json: {_render_permission_rule(mismatch.current_value)}",
            ]
        )
    return lines


def _render_server_line(server: ServerStatusDocument) -> str:
    if not server.running or server.base_url is None:
        return "Server: not found on configured/default probe URLs"

    server_line = f"Server: UP {server.base_url}"
    if server.version is not None:
        server_line += f" ({server.version})"
    return server_line


def _render_active_tool_lines(report: DoctorReportDocument) -> list[str]:
    if report.tool_scan_error is not None:
        return [
            "OpenCode tools:",
            "  In Global Policy? [x] means policies.global explicitly includes a",
            "  permission for this OpenCode tool.",
            f"  unavailable ({report.tool_scan_error})",
        ]
    if report.tool_permissions:
        return [
            "OpenCode tools:",
            "  In Global Policy? [x] means policies.global explicitly includes a",
            "  permission for this OpenCode tool.",
            *[
                f"  {_checkbox(status.explicit_permission)} {status.name}"
                for status in report.tool_permissions
            ],
        ]
    if report.server.running:
        return [
            "OpenCode tools:",
            "  In Global Policy? [x] means policies.global explicitly includes a",
            "  permission for this OpenCode tool.",
            "  none",
        ]
    return []


def _render_non_tool_permission_lines(
    non_tool_permissions: list[NonToolPermissionStatus],
    tool_scan_error: str | None,
) -> list[str]:
    if tool_scan_error is not None:
        return [
            "OpenCode non-tool permissions:",
            "  In Global Policy? [x] means policies.global explicitly includes this",
            "  OpenCode permission.",
            f"  unavailable ({tool_scan_error})",
        ]
    if not non_tool_permissions:
        return []
    return [
        "OpenCode non-tool permissions:",
        "  In Global Policy? [x] means policies.global explicitly includes this",
        "  OpenCode permission.",
        *[
            f"  {_checkbox(status.explicit_permission)} {status.name}"
            for status in non_tool_permissions
        ],
    ]


def _render_inactive_permission_lines(
    inactive_configured_permissions: list[str],
    tool_scan_error: str | None,
) -> list[str]:
    if tool_scan_error is not None:
        return [
            "Policy permissions without a current OpenCode tool:",
            f"  unavailable ({tool_scan_error})",
        ]
    if inactive_configured_permissions:
        return [
            "Policy permissions without a current OpenCode tool:",
            "  These permissions are present in policies.global but were not found",
            "  in the live OpenCode tool inventory. They may be policy entries for",
            "  tools that no longer exist, or local tool discovery may still be",
            "  missing a tool the server should expose.",
            *[f"  [!] {name}" for name in inactive_configured_permissions],
        ]
    return [
        "Policy permissions without a current OpenCode tool:",
        "  none",
    ]


def _render_permission_rule(rule: PermissionRule) -> str:
    if isinstance(rule, str):
        return rule
    return json.dumps(rule, sort_keys=True)


def _server_can_list_tools(server_status: ServerStatusDocument) -> bool:
    return server_status.running and server_status.base_url is not None


def _fetch_live_tool_ids(base_url: str) -> tuple[list[str] | None, str | None]:
    try:
        return _fetch_tool_ids(base_url), None
    except ConfigError as exc:
        return None, str(exc)


def _discover_known_tool_ids(
    *,
    server_status: ServerStatusDocument,
    configured_mcp_servers: list[str],
    mcp_servers: dict[
        str,
        McpLocalServerDocument | McpRemoteServerDocument | McpDisabledServerDocument,
    ]
    | None,
) -> tuple[list[str] | None, str | None]:
    if server_status.base_url is None:
        return None, "OpenCode server is unavailable"

    tool_ids, tool_scan_error = _fetch_live_tool_ids(server_status.base_url)
    if tool_scan_error is not None or tool_ids is None:
        return None, tool_scan_error

    mcp_tool_ids, mcp_scan_error = _discover_mcp_tool_ids(
        configured_mcp_servers=configured_mcp_servers,
        mcp_servers=mcp_servers,
    )
    if mcp_scan_error is not None:
        return None, mcp_scan_error

    return _dedupe_tool_ids([*tool_ids, *mcp_tool_ids]), None


def _tool_permission_statuses(
    tool_ids: list[str],
    explicit_permissions: set[str],
) -> list[ToolPermissionStatus]:
    return [
        ToolPermissionStatus(
            name=tool_id,
            explicit_permission=tool_id in explicit_permissions,
        )
        for tool_id in sorted(tool_ids)
    ]


def _non_tool_permission_statuses(
    global_policy_permissions: dict[str, PermissionRule] | None,
) -> list[NonToolPermissionStatus]:
    if global_policy_permissions is None:
        return []
    explicit_permissions = set(global_policy_permissions)
    return [
        NonToolPermissionStatus(
            name=name,
            explicit_permission=name in explicit_permissions,
        )
        for name in NON_TOOL_PERMISSION_KEYS
    ]


def _inactive_configured_permissions(
    tool_ids: list[str],
    explicit_permissions: set[str],
) -> list[str]:
    return sorted(
        key
        for key in explicit_permissions
        if key not in tool_ids
        and key not in NON_TOOL_PERMISSION_KEYS
        and key != GLOBAL_PERMISSION_DEFAULT_KEY
    )


def _dedupe_tool_ids(tool_ids: list[str]) -> list[str]:
    deduped: list[str] = []
    for tool_id in tool_ids:
        if tool_id not in deduped:
            deduped.append(tool_id)
    return deduped


def _discover_mcp_tool_ids(
    *,
    configured_mcp_servers: list[str],
    mcp_servers: dict[
        str,
        McpLocalServerDocument | McpRemoteServerDocument | McpDisabledServerDocument,
    ]
    | None,
) -> tuple[list[str], str | None]:
    if not configured_mcp_servers:
        return [], None
    if mcp_servers is None:
        return [], "Global config could not be parsed for configured MCP tool discovery"

    discovered: list[str] = []
    for server_name in configured_mcp_servers:
        tool_names, error = _discover_mcp_tool_names_for_server(server_name, mcp_servers)
        if error is not None:
            return [], error
        discovered.extend(_mcp_permission_key(server_name, tool_name) for tool_name in tool_names)
    return discovered, None


def _discover_mcp_tool_names_for_server(
    server_name: str,
    mcp_servers: dict[
        str,
        McpLocalServerDocument | McpRemoteServerDocument | McpDisabledServerDocument,
    ],
) -> tuple[list[str], str | None]:
    config, config_error = _configured_mcp_server(server_name, mcp_servers)
    if config_error is not None or config is None:
        return [], config_error
    return _fetch_mcp_tool_names(server_name, config)


def _configured_mcp_server(
    server_name: str,
    mcp_servers: dict[
        str,
        McpLocalServerDocument | McpRemoteServerDocument | McpDisabledServerDocument,
    ],
) -> tuple[McpLocalServerDocument | McpRemoteServerDocument | None, str | None]:
    config = mcp_servers.get(server_name)
    if config is None:
        msg = f"Configured MCP server {server_name!r} is missing from the global OpenCode config"
        return None, msg
    if isinstance(config, McpDisabledServerDocument) or getattr(config, "enabled", True) is False:
        msg = f"Configured MCP server {server_name!r} is disabled in the global OpenCode config"
        return None, msg
    return config, None


def _fetch_mcp_tool_names(
    server_name: str,
    config: McpLocalServerDocument | McpRemoteServerDocument,
) -> tuple[list[str], str | None]:
    command = _mcp2cli_command(config)
    timeout_seconds = _mcp_timeout_seconds(config)
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except OSError as exc:
        return [], f"Failed to execute mcp2cli for MCP server {server_name!r}: {exc}"
    except subprocess.TimeoutExpired:
        detail = (
            f"mcp2cli timed out for MCP server {server_name!r}"
            if timeout_seconds is None
            else f"mcp2cli timed out for MCP server {server_name!r} after {timeout_seconds:g}s"
        )
        return [], detail

    if process.returncode != 0:
        detail = (
            process.stderr.strip() or process.stdout.strip() or f"exit code {process.returncode}"
        )
        return [], f"mcp2cli failed for MCP server {server_name!r}: {detail}"

    return _parse_mcp2cli_tool_names(process.stdout), None


def _mcp2cli_command(
    config: McpLocalServerDocument | McpRemoteServerDocument,
) -> list[str]:
    if isinstance(config, McpLocalServerDocument):
        return _mcp2cli_local_command(config)
    return _mcp2cli_remote_command(config)


def _mcp2cli_base_command() -> list[str]:
    return [sys.executable, "-m", mcp2cli.__name__]


def _mcp2cli_local_command(config: McpLocalServerDocument) -> list[str]:
    command = _mcp2cli_base_command()
    command.extend(["--mcp-stdio", shlex.join(config.command)])
    for key, value in sorted((config.environment or {}).items()):
        command.extend(["--env", f"{key}={value}"])
    command.extend(["--list", "--toon"])
    return command


def _mcp2cli_remote_command(config: McpRemoteServerDocument) -> list[str]:
    command = _mcp2cli_base_command()
    command.extend(["--mcp", config.url])
    for key, value in sorted((config.headers or {}).items()):
        command.extend(["--auth-header", f"{key}:{_translate_config_value(value)}"])
    command.extend(_mcp2cli_oauth_args(config))
    command.extend(["--list", "--toon"])
    return command


def _mcp2cli_oauth_args(config: McpRemoteServerDocument) -> list[str]:
    if config.oauth is None or config.oauth is False:
        return []

    args = ["--oauth"]
    if config.oauth.clientId is not None:
        args.extend(["--oauth-client-id", _translate_config_value(config.oauth.clientId)])
    if config.oauth.clientSecret is not None:
        args.extend(["--oauth-client-secret", _translate_config_value(config.oauth.clientSecret)])
    if config.oauth.scope is not None:
        args.extend(["--oauth-scope", config.oauth.scope])
    return args


def _parse_mcp2cli_tool_names(output: str) -> list[str]:
    tool_names: list[str] = []
    for line in output.splitlines():
        if not line.startswith("  ") or line.startswith("   "):
            continue
        parts = line.split()
        if not parts:
            continue
        tool_names.append(parts[0])
    return tool_names


def _mcp_permission_key(server_name: str, tool_name: str) -> str:
    return f"{server_name}_{tool_name.replace('-', '_')}"


def _translate_config_value(value: str) -> str:
    match = re.fullmatch(r"\{(?P<kind>env|file):(?P<body>.+)\}", value)
    if match is None:
        return value
    return f"{match.group('kind')}:{match.group('body')}"


def _mcp_timeout_seconds(config: McpLocalServerDocument | McpRemoteServerDocument) -> float | None:
    if config.timeout is None:
        return None
    return config.timeout / 1000


@validate_call
def build_install_config_text(
    *,
    configured_mcp_servers: list[str],
    known_tool_ids: list[str],
) -> str:
    global_policy: dict[str, PermissionAction] = {
        tool_id: "allow" for tool_id in sorted(known_tool_ids)
    }
    global_policy.update(NON_TOOL_PERMISSION_DEFAULTS)

    lines = [
        "# OpenCode permission policy compiler configuration.",
        "# MCP names here are resolved against ~/.config/opencode/opencode.json.",
        "[mcps]",
        "# MCP servers whose tools should be included in doctor/install-config inventory.",
        f"servers = {json.dumps(sorted(configured_mcp_servers))}",
        "",
        f"[policies.{GLOBAL_POLICY_NAME}]",
        *[f'{key} = "{value}"' for key, value in global_policy.items()],
        "",
        "[policies.subagents]",
        *SUBAGENTS_POLICY_LINES,
        "",
        *COMMENTED_GLOBAL_POLICY_GUIDANCE,
    ]
    return "\n".join(lines) + "\n"


@validate_call
def enabled_mcp_server_names(
    mcp_servers: dict[
        str,
        McpLocalServerDocument | McpRemoteServerDocument | McpDisabledServerDocument,
    ],
) -> list[str]:
    return sorted(
        name
        for name, config in mcp_servers.items()
        if not isinstance(config, McpDisabledServerDocument)
        and getattr(config, "enabled", True) is not False
    )
