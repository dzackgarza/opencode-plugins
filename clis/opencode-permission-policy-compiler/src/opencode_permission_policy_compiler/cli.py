from __future__ import annotations

import sys
from pathlib import Path

import yaml
from cyclopts import App
from pydantic import validate_call

from .config import (
    STANDARD_GLOBAL_CONFIG_PATH,
    load_global_config_document,
    load_global_permission_base,
    load_known_policies,
    load_policy_catalog_document,
    policy_config_path,
    write_global_permission_base,
    write_policy_config_text,
)
from .errors import CompilerError
from .logic import (
    _detect_server,
    _discover_known_tool_ids,
    build_doctor_report,
    build_install_config_text,
    compile_markdown_agent,
    compute_minimal_global_permissions,
    doctor_exit_code,
    enabled_mcp_server_names,
    render_doctor_report,
    resolve_policy_permissions,
)
from .models import DoctorInputDocument, PermissionFragmentData, PermissionRule

app = App(
    name="opencode-permission-policy-compiler",
    help="Compile policy-tagged OpenCode markdown agents into explicit permission metadata.",
)


@app.default
@validate_call
def compile_agent() -> None:
    """Compile one markdown agent from stdin to stdout."""
    source = sys.stdin.read()
    if not source:
        msg = "Expected markdown agent content on stdin"
        raise CompilerError(msg)

    base_permissions = load_global_permission_base()
    known_policies = load_known_policies()
    sys.stdout.write(compile_markdown_agent(source, base_permissions, known_policies))


@app.command
@validate_call
def list_policies() -> None:
    """Print the resolved policy catalog."""
    sys.stdout.write(
        yaml.safe_dump(
            load_known_policies(),
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
    )


@app.command
@validate_call
def set_global_policy(policy: str) -> None:
    """Overwrite the global OpenCode permission config with one resolved policy."""
    known_policies = load_known_policies()
    resolved_permissions = resolve_policy_permissions(
        policy_names=[policy],
        known_policies=known_policies,
        base_permissions={},
    )
    written_path = write_global_permission_base(
        compute_minimal_global_permissions(resolved_permissions)
    )
    sys.stdout.write(f"{Path(written_path).expanduser()}\n")


@app.command
@validate_call
def install_config() -> None:
    """Install a baseline XDG policy config from the live OpenCode tool inventory."""
    global_config = load_global_config_document()
    mcp_servers = global_config.resolved_mcp()
    configured_mcp_servers = enabled_mcp_server_names(mcp_servers)
    server_status = _detect_server(global_config.server_base_urls())
    known_tool_ids, error = _discover_known_tool_ids(
        server_status=server_status,
        configured_mcp_servers=configured_mcp_servers,
        mcp_servers=mcp_servers,
    )
    if error is not None or known_tool_ids is None:
        msg = error or "Failed to discover live OpenCode tools"
        raise CompilerError(msg)

    content = build_install_config_text(
        configured_mcp_servers=configured_mcp_servers,
        known_tool_ids=known_tool_ids,
    )
    written_path = write_policy_config_text(content)
    sys.stdout.write(f"{Path(written_path).expanduser()}\n")


@app.command
@validate_call
def doctor() -> None:
    """Inspect policy config, global permission parsing, and live OpenCode tool coverage."""
    policy_error: str | None = None
    global_error: str | None = None
    global_policy_permissions: dict[str, PermissionRule] | None = None
    known_policies: dict[str, PermissionFragmentData] | None = None
    current_permissions: dict[str, PermissionRule] | None = None
    configured_mcp_servers: list[str] = []
    server_base_urls: list[str] = []
    mcp_servers = None

    try:
        policy_catalog = load_policy_catalog_document()
        known_policies = policy_catalog.resolved_policies()
        configured_mcp_servers = policy_catalog.configured_mcp_servers()
        global_policy_permissions = policy_catalog.resolved_global_policy()
        if global_policy_permissions is None:
            msg = "CLI policy config must define [policies.global]"
            raise CompilerError(msg)
    except CompilerError as exc:
        policy_error = str(exc)

    try:
        global_config = load_global_config_document()
        current_permissions = global_config.resolved_permission()
        server_base_urls = global_config.server_base_urls()
        mcp_servers = global_config.resolved_mcp()
    except CompilerError as exc:
        global_error = str(exc)

    report = build_doctor_report(
        DoctorInputDocument(
            policy_config_path=policy_config_path(),
            global_config_path=STANDARD_GLOBAL_CONFIG_PATH,
            global_policy_permissions=global_policy_permissions,
            current_permissions=current_permissions,
            known_policies=known_policies,
            policy_config_error=policy_error,
            global_config_error=global_error,
            server_base_urls=server_base_urls,
            configured_mcp_servers=configured_mcp_servers,
            mcp_servers=mcp_servers,
        )
    )
    sys.stdout.write(render_doctor_report(report))
    raise SystemExit(doctor_exit_code(report))


def main() -> None:
    try:
        app()
    except CompilerError as exc:
        raise SystemExit(str(exc)) from exc
