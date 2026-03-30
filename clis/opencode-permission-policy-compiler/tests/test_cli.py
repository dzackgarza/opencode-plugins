from __future__ import annotations

import contextlib
import json
import re
import subprocess
import tomllib
from collections.abc import Iterator
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from os import environ
from pathlib import Path
from threading import Thread
from typing import cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_TEMPLATE_PATH = REPO_ROOT / "config.toml"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
FRONTMATTER_PATTERN = re.compile(
    r"\A---\n(?P<frontmatter>.*?)\n---\n(?P<body>[\s\S]*)\Z",
    re.DOTALL,
)

REPRESENTATIVE_GLOBAL_PERMISSION: dict[str, object] = {
    "read": "allow",
    "glob": "allow",
    "grep": "allow",
    "edit": "allow",
    "apply_patch": "allow",
    "webfetch": "allow",
    "websearch": "allow",
    "todowrite": "allow",
    "todoread": "allow",
    "task": "allow",
    "question": "allow",
    "external_directory": {
        "*": "ask",
        "/home/dzack/ai/*": "allow",
        "/home/dzack/.plannotator/*": "allow",
        "/tmp/*": "allow",
    },
    "list_sessions": "allow",
    "introspection": "allow",
    "read_transcript": "allow",
    "submit_plan": "allow",
    "plannotator_review": "allow",
    "plannotator_annotate": "allow",
    "write": "allow",
}

SUBAGENT_POLICY_EFFECTIVE: dict[str, str] = {
    "task": "deny",
    "question": "deny",
    "submit_plan": "deny",
    "plannotator_review": "deny",
    "plannotator_annotate": "deny",
}


def compute_minimal_global_permissions_for_test(
    policy_permissions: dict[str, object],
) -> dict[str, object]:
    minimal: dict[str, object] = {}
    for key, value in policy_permissions.items():
        default_action = "ask" if key in {"external_directory", "doom_loop"} else "allow"
        if isinstance(value, str):
            if value != default_action:
                minimal[key] = value
            continue
        assert isinstance(value, dict)
        minimized_rules = {
            inner_key: inner_value
            for inner_key, inner_value in value.items()
            if inner_value != default_action
        }
        if minimized_rules:
            minimal[key] = minimized_rules
    effective_default = policy_permissions.get("*")
    if isinstance(effective_default, str) and minimal.get("*") == effective_default:
        for key, value in policy_permissions.items():
            if key in {"*", "external_directory", "doom_loop"}:
                continue
            if not isinstance(value, str) or value == effective_default or key in minimal:
                continue
            minimal[key] = value
    return minimal


def run_cli(
    markdown_text: str,
    *args: str,
    home: Path,
    xdg_config_home: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(environ)
    env["HOME"] = str(home)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    if xdg_config_home is not None:
        env["XDG_CONFIG_HOME"] = str(xdg_config_home)
    return subprocess.run(
        ["uv", "run", "python", "-m", "opencode_permission_policy_compiler", *args],
        input=markdown_text,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        env=env,
        check=False,
    )


def run_doctor_report(home: Path, xdg_config_home: Path) -> dict[str, object]:
    env = dict(environ)
    env["HOME"] = str(home)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["XDG_CONFIG_HOME"] = str(xdg_config_home)
    script = """
import json
from opencode_permission_policy_compiler.cli import STANDARD_GLOBAL_CONFIG_PATH, policy_config_path
from opencode_permission_policy_compiler.config import (
    load_global_config_document,
    load_policy_catalog_document,
)
from opencode_permission_policy_compiler.errors import CompilerError
from opencode_permission_policy_compiler.logic import build_doctor_report
from opencode_permission_policy_compiler.models import DoctorInputDocument

policy_error = None
global_error = None
global_policy_permissions = None
known_policies = None
current_permissions = None
configured_mcp_servers = []
server_base_urls = []
mcp_servers = None

try:
    policy_catalog = load_policy_catalog_document()
    known_policies = policy_catalog.resolved_policies()
    configured_mcp_servers = policy_catalog.configured_mcp_servers()
    global_policy_permissions = policy_catalog.resolved_global_policy()
    if global_policy_permissions is None:
        raise CompilerError("CLI policy config must define [policies.global]")
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
print(report.model_dump_json())
"""
    result = subprocess.run(
        ["uv", "run", "python", "-c", script],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return cast(dict[str, object], json.loads(result.stdout))


def parse_output(markdown_text: str) -> tuple[dict[str, object], str]:
    match = FRONTMATTER_PATTERN.match(markdown_text)
    assert match is not None, markdown_text
    raw_metadata = yaml.safe_load(match.group("frontmatter"))
    assert isinstance(raw_metadata, dict)
    metadata = cast(dict[str, object], raw_metadata)
    return metadata, match.group("body")


def strip_permission_from_fixture(markdown_text: str) -> str:
    metadata, body = parse_output(markdown_text)
    metadata.pop("permission", None)
    metadata.pop("tools", None)
    yaml_text = yaml.safe_dump(
        metadata,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).strip()
    return f"---\n{yaml_text}\n---\n{body}"


def replace_permission_in_fixture(
    markdown_text: str,
    permission: dict[str, object],
) -> str:
    metadata, body = parse_output(markdown_text)
    metadata["permission"] = permission
    yaml_text = yaml.safe_dump(
        metadata,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).strip()
    return f"---\n{yaml_text}\n---\n{body}"


def write_global_config(tmp_path: Path, permission: dict[str, object]) -> Path:
    return write_global_payload(tmp_path, {"permission": permission})


def write_global_payload(tmp_path: Path, payload: dict[str, object]) -> Path:
    config_path = tmp_path / ".config" / "opencode" / "opencode.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return config_path


def install_policy_config(xdg_config_home: Path, content: str | None = None) -> Path:
    config_path = xdg_config_home / "opencode-permission-policy-compiler" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if content is None:
        content = with_configured_mcps(
            CONFIG_TEMPLATE_PATH.read_text(encoding="utf-8"),
            [],
        )
    config_path.write_text(content, encoding="utf-8")
    return config_path


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def read_global_config(tmp_path: Path) -> dict[str, object]:
    config_path = tmp_path / ".config" / "opencode" / "opencode.json"
    return cast(
        dict[str, object],
        json.loads(config_path.read_text(encoding="utf-8")),
    )


def read_policy_config() -> dict[str, object]:
    return cast(dict[str, object], tomllib.loads(CONFIG_TEMPLATE_PATH.read_text(encoding="utf-8")))


def build_policy_config(
    *,
    global_policy: dict[str, object],
    mcps: list[str] | None = None,
) -> str:
    lines = [
        "[mcps]",
        f"servers = {json.dumps(sorted(mcps or []))}",
        "",
        "[policies.global]",
    ]
    deferred_tables: list[tuple[str, dict[str, str]]] = []
    for key, value in global_policy.items():
        if isinstance(value, dict):
            deferred_tables.append((key, cast(dict[str, str], value)))
            continue
        rendered_key = json.dumps(key) if not key.isidentifier() else key
        lines.append(f"{rendered_key} = {json.dumps(value)}")
    for key, value in deferred_tables:
        lines.extend(
            [
                "",
                f"[policies.global.{key}]",
                *[
                    f"{json.dumps(inner_key)} = {json.dumps(inner_value)}"
                    for inner_key, inner_value in value.items()
                ],
            ]
        )
    lines.extend(
        [
            "",
            "[policies.subagents]",
            'task = "deny"',
            'question = "deny"',
            'submit_plan = "deny"',
            'plannotator_review = "deny"',
            'plannotator_annotate = "deny"',
            "",
        ]
    )
    return "\n".join(lines)


def with_configured_mcps(content: str, server_names: list[str]) -> str:
    remainder = "\n".join(
        line
        for line in content.splitlines()
        if not line.startswith("[mcps]") and not line.startswith("servers = ")
    ).lstrip("\n")
    mcps_block = "[mcps]\n" + f"servers = {server_names!r}\n\n"
    return mcps_block + remainder


def merge_permissions(
    base_permissions: dict[str, object],
    overlay_permissions: dict[str, object],
) -> dict[str, object]:
    merged = deepcopy(base_permissions)
    merged.update(deepcopy(overlay_permissions))
    return merged


@contextlib.contextmanager
def running_tool_server(
    *,
    tool_ids: list[str],
    version: str = "test-version",
) -> Iterator[ThreadingHTTPServer]:
    def do_get(self: BaseHTTPRequestHandler) -> None:
        payload_by_path = {
            "/global/health": {"healthy": True, "version": version},
            "/experimental/tool/ids": tool_ids,
        }
        write_json(self, payload_by_path[self.path])

    def log_message(
        self: BaseHTTPRequestHandler,
        message_format: str,
        *args: object,
    ) -> None:
        del self, message_format, args

    def write_json(self: BaseHTTPRequestHandler, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    handler_type = type(
        "Handler",
        (BaseHTTPRequestHandler,),
        {
            "do_GET": do_get,
            "log_message": log_message,
            "_write_json": write_json,
        },
    )

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_type)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_cli_maps_real_prover_subagent_input_to_current_agent_markdown_exactly(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    write_global_config(tmp_path, REPRESENTATIVE_GLOBAL_PERMISSION)
    install_policy_config(xdg_config_home)
    expected = read_fixture("prover-subagent-output.md")
    source = strip_permission_from_fixture(expected)

    result = run_cli(source, home=tmp_path, xdg_config_home=xdg_config_home)

    assert result.returncode == 0, result.stderr
    assert result.stdout == expected


def test_cli_only_emits_permission_entries_that_change_relative_to_global_baseline(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    base_permissions = deepcopy(REPRESENTATIVE_GLOBAL_PERMISSION)
    base_permissions["task"] = "deny"
    base_permissions["question"] = "deny"
    write_global_config(tmp_path, base_permissions)
    install_policy_config(xdg_config_home)
    source = strip_permission_from_fixture(read_fixture("prover-subagent-output.md"))

    result = run_cli(source, home=tmp_path, xdg_config_home=xdg_config_home)

    assert result.returncode == 0, result.stderr
    metadata, body = parse_output(result.stdout)
    overlay = cast(dict[str, object], metadata["permission"])
    effective = merge_permissions(base_permissions, overlay)

    assert overlay == {
        "submit_plan": "deny",
        "plannotator_review": "deny",
        "plannotator_annotate": "deny",
    }
    assert effective["task"] == "deny"
    assert effective["question"] == "deny"
    assert effective["submit_plan"] == "deny"
    assert effective["plannotator_review"] == "deny"
    assert effective["plannotator_annotate"] == "deny"
    assert effective["todowrite"] == "allow"
    assert body == parse_output(source)[1]


def test_cli_merges_existing_agent_permission_with_policy_overlay(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    write_global_config(tmp_path, REPRESENTATIVE_GLOBAL_PERMISSION)
    install_policy_config(xdg_config_home)
    source = replace_permission_in_fixture(
        read_fixture("prover-subagent-output.md"),
        {
            "read": "deny",
            "submit_plan": "ask",
        },
    )

    result = run_cli(source, home=tmp_path, xdg_config_home=xdg_config_home)

    assert result.returncode == 0, result.stderr
    metadata, body = parse_output(result.stdout)
    overlay = cast(dict[str, object], metadata["permission"])
    effective = merge_permissions(REPRESENTATIVE_GLOBAL_PERMISSION, overlay)

    assert overlay == {
        "read": "deny",
        "task": "deny",
        "question": "deny",
        "submit_plan": "deny",
        "plannotator_review": "deny",
        "plannotator_annotate": "deny",
    }
    assert effective["read"] == "deny"
    assert effective["submit_plan"] == "deny"
    assert effective["task"] == "deny"
    assert effective["question"] == "deny"
    assert body == parse_output(source)[1]


def test_cli_omits_permission_block_when_global_baseline_already_matches_subagent_policy(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    base_permissions = deepcopy(REPRESENTATIVE_GLOBAL_PERMISSION)
    base_permissions.update(SUBAGENT_POLICY_EFFECTIVE)
    write_global_config(tmp_path, base_permissions)
    install_policy_config(xdg_config_home)
    source = strip_permission_from_fixture(read_fixture("prover-subagent-output.md"))

    result = run_cli(source, home=tmp_path, xdg_config_home=xdg_config_home)

    assert result.returncode == 0, result.stderr
    metadata, body = parse_output(result.stdout)

    assert "permission" not in metadata
    assert "policies" not in metadata
    assert body == parse_output(source)[1]


def test_cli_treats_missing_global_entries_as_runtime_defaults_when_minimizing(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    write_global_config(
        tmp_path,
        {
            "invalid": "deny",
        },
    )
    install_policy_config(xdg_config_home)
    source = """---
name: Default-Allow Agent
mode: primary
description: Explicit allow should collapse against runtime defaults
permission:
  read: allow
  external_directory:
    "*": ask
    "/tmp/*": allow
---
Use runtime-default-aware minimization.
"""

    result = run_cli(source, home=tmp_path, xdg_config_home=xdg_config_home)

    assert result.returncode == 0, result.stderr
    metadata, body = parse_output(result.stdout)
    assert metadata["permission"] == {
        "external_directory": {
            "/tmp/*": "allow",
        }
    }
    assert body == "Use runtime-default-aware minimization.\n"


def test_cli_preserves_allow_exceptions_under_deny_wildcards(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    write_global_config(tmp_path, {"read": "allow"})
    install_policy_config(xdg_config_home)
    source = """---
name: Scoped Agent
mode: primary
description: Preserve allow exceptions under deny wildcard
permission:
  edit:
    "*": deny
    ".agents/*": allow
  bash:
    "*": deny
    "git": allow
    "git *": allow
---
Preserve scoped allow exceptions.
"""

    result = run_cli(source, home=tmp_path, xdg_config_home=xdg_config_home)

    assert result.returncode == 0, result.stderr
    metadata, body = parse_output(result.stdout)
    assert metadata["permission"] == {
        "edit": {
            "*": "deny",
            ".agents/*": "allow",
        },
        "bash": {
            "*": "deny",
            "git": "allow",
            "git *": "allow",
        },
    }
    assert body == "Preserve scoped allow exceptions.\n"


def test_cli_preserves_scalar_allow_exceptions_under_deny_wildcard(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    write_global_config(
        tmp_path,
        {
            "read": "allow",
            "task": "allow",
            "todowrite": "allow",
        },
    )
    install_policy_config(xdg_config_home)
    source = """---
name: Restricted Agent
mode: primary
description: Preserve scalar allow exceptions under deny wildcard
permission:
  "*": deny
  read: allow
  task: allow
  todowrite: allow
---
Preserve scalar allow exceptions.
"""

    result = run_cli(source, home=tmp_path, xdg_config_home=xdg_config_home)

    assert result.returncode == 0, result.stderr
    metadata, body = parse_output(result.stdout)
    assert metadata["permission"] == {
        "*": "deny",
        "read": "allow",
        "task": "allow",
        "todowrite": "allow",
    }
    assert body == "Preserve scalar allow exceptions.\n"


def test_cli_rejects_unknown_policy_without_emitting_compiled_markdown(tmp_path: Path) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    write_global_config(tmp_path, REPRESENTATIVE_GLOBAL_PERMISSION)
    install_policy_config(xdg_config_home)
    source = read_fixture("unknown-policy-subagent.md")

    result = run_cli(source, home=tmp_path, xdg_config_home=xdg_config_home)

    assert result.returncode != 0
    assert result.stdout == ""


def test_cli_rejects_legacy_tools_frontmatter_without_emitting_compiled_markdown(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    write_global_config(tmp_path, REPRESENTATIVE_GLOBAL_PERMISSION)
    install_policy_config(xdg_config_home)
    source = read_fixture("prover-subagent-legacy-tools.md")

    result = run_cli(source, home=tmp_path, xdg_config_home=xdg_config_home)

    assert result.returncode != 0
    assert result.stdout == ""


def test_cli_fails_when_standard_global_config_is_missing(tmp_path: Path) -> None:
    source = strip_permission_from_fixture(read_fixture("prover-subagent-output.md"))

    result = run_cli(source, home=tmp_path)

    assert result.returncode != 0
    assert result.stdout == ""


def test_cli_allows_non_subagent_markdown_without_explicit_policies(tmp_path: Path) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    write_global_config(tmp_path, REPRESENTATIVE_GLOBAL_PERMISSION)
    install_policy_config(xdg_config_home)
    source = read_fixture("primary-agent-no-policies.md")

    result = run_cli(source, home=tmp_path, xdg_config_home=xdg_config_home)

    assert result.returncode == 0, result.stderr
    metadata, body = parse_output(result.stdout)

    assert "permission" not in metadata
    assert "policies" not in metadata
    assert body == parse_output(source)[1]


def test_cli_orders_generated_metadata_with_model_before_mode_and_permission_last(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    write_global_config(tmp_path, REPRESENTATIVE_GLOBAL_PERMISSION)
    install_policy_config(xdg_config_home)
    source = """---
name: Ordered Subagent
model: openai/gpt-5.4
mode: subagent
description: Checks generated frontmatter ordering
---
Verify ordering.
"""

    result = run_cli(source, home=tmp_path, xdg_config_home=xdg_config_home)

    assert result.returncode == 0, result.stderr
    metadata, body = parse_output(result.stdout)

    assert list(metadata) == ["name", "model", "mode", "description", "permission"]
    assert cast(dict[str, object], metadata["permission"]) == {
        "task": "deny",
        "question": "deny",
        "submit_plan": "deny",
        "plannotator_review": "deny",
        "plannotator_annotate": "deny",
    }
    assert body == "Verify ordering.\n"


def test_set_global_policy_overwrites_permission_and_preserves_other_global_config(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    install_policy_config(xdg_config_home)
    write_global_payload(
        tmp_path,
        {
            "$schema": "https://opencode.ai/config.json",
            "model": "openrouter/some-model",
            "permission": {
                "read": "deny",
                "external_directory": {
                    "*": "deny",
                },
            },
            "formatter": {
                "format": "json",
            },
        },
    )

    result = run_cli(
        "",
        "set-global-policy",
        "global",
        home=tmp_path,
        xdg_config_home=xdg_config_home,
    )

    expected_permission = compute_minimal_global_permissions_for_test(
        cast(dict[str, object], cast(dict[str, object], read_policy_config()["policies"])["global"])
    )
    rewritten = read_global_config(tmp_path)

    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == tmp_path / ".config" / "opencode" / "opencode.json"
    assert rewritten["permission"] == expected_permission
    assert rewritten["model"] == "openrouter/some-model"
    assert rewritten["formatter"] == {"format": "json"}


def test_set_global_policy_omits_default_allow_entries_and_default_ask_rules(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    install_policy_config(
        xdg_config_home,
        content=build_policy_config(
            global_policy={
                "read": "allow",
                "question": "deny",
                "doom_loop": "ask",
                "external_directory": {
                    "*": "ask",
                    "/tmp/*": "allow",
                },
            }
        ),
    )
    write_global_payload(tmp_path, {"permission": {"read": "deny"}})

    result = run_cli(
        "",
        "set-global-policy",
        "global",
        home=tmp_path,
        xdg_config_home=xdg_config_home,
    )

    rewritten = read_global_config(tmp_path)

    assert result.returncode == 0, result.stderr
    assert rewritten["permission"] == {
        "question": "deny",
        "external_directory": {
            "/tmp/*": "allow",
        },
    }


def test_set_global_policy_preserves_allow_exceptions_under_deny_wildcards(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    install_policy_config(
        xdg_config_home,
        content=build_policy_config(
            global_policy={
                "edit": {
                    "*": "deny",
                    ".agents/*": "allow",
                },
                "bash": {
                    "*": "deny",
                    "git": "allow",
                    "git *": "allow",
                },
            }
        ),
    )
    write_global_payload(tmp_path, {"permission": {"read": "allow"}})

    result = run_cli(
        "",
        "set-global-policy",
        "global",
        home=tmp_path,
        xdg_config_home=xdg_config_home,
    )

    rewritten = read_global_config(tmp_path)

    assert result.returncode == 0, result.stderr
    assert rewritten["permission"] == {
        "edit": {
            "*": "deny",
            ".agents/*": "allow",
        },
        "bash": {
            "*": "deny",
            "git": "allow",
            "git *": "allow",
        },
    }


def test_set_global_policy_preserves_scalar_allow_exceptions_under_deny_wildcard(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    install_policy_config(
        xdg_config_home,
        content=build_policy_config(
            global_policy={
                "*": "deny",
                "read": "allow",
                "task": "allow",
                "todowrite": "allow",
            }
        ),
    )
    write_global_payload(tmp_path, {"permission": {"read": "allow"}})

    result = run_cli(
        "",
        "set-global-policy",
        "global",
        home=tmp_path,
        xdg_config_home=xdg_config_home,
    )

    rewritten = read_global_config(tmp_path)

    assert result.returncode == 0, result.stderr
    assert rewritten["permission"] == {
        "*": "deny",
        "read": "allow",
        "task": "allow",
        "todowrite": "allow",
    }


def test_list_policies_prints_resolved_policy_map(tmp_path: Path) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    install_policy_config(xdg_config_home)

    result = run_cli(
        "",
        "list-policies",
        home=tmp_path,
        xdg_config_home=xdg_config_home,
    )

    listed = yaml.safe_load(result.stdout)
    assert result.returncode == 0, result.stderr
    assert listed == cast(dict[str, object], read_policy_config()["policies"])


def test_set_global_policy_replaces_previous_external_directory_rules_with_policy_payload(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    install_policy_config(xdg_config_home)
    write_global_payload(
        tmp_path,
        {
            "permission": {
                "read": "allow",
                "external_directory": {
                    "*": "ask",
                    "/tmp/*": "allow",
                },
            },
        },
    )

    result = run_cli(
        "",
        "set-global-policy",
        "subagents",
        home=tmp_path,
        xdg_config_home=xdg_config_home,
    )

    rewritten = read_global_config(tmp_path)
    permission = cast(dict[str, object], rewritten["permission"])

    assert result.returncode == 0, result.stderr
    assert permission == SUBAGENT_POLICY_EFFECTIVE
    assert "external_directory" not in permission


def test_doctor_reports_applied_global_policy_live_tool_coverage_and_non_tool_permissions(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    global_policy = {
        "read": "allow",
        "task": "allow",
        "external_directory": "ask",
        "doom_loop": "ask",
    }
    install_policy_config(
        xdg_config_home,
        content=build_policy_config(global_policy=global_policy),
    )
    tool_ids = ["read", "task", "todoread"]

    with running_tool_server(tool_ids=tool_ids, version="9.9.9") as server:
        write_global_payload(
            tmp_path,
            {
                "permission": compute_minimal_global_permissions_for_test(global_policy),
                "server": {
                    "hostname": "127.0.0.1",
                    "port": server.server_port,
                },
            },
        )

        report = run_doctor_report(tmp_path, xdg_config_home)

    assert report["policy_config_valid"] is True
    assert report["global_policy_applied"] is True
    assert cast(dict[str, object], report["server"])["running"] is True
    assert cast(dict[str, object], report["server"])["version"] == "9.9.9"
    assert {
        status["name"]: status["explicit_permission"]
        for status in cast(list[dict[str, object]], report["tool_permissions"])
    } == {
        "read": True,
        "task": True,
        "todoread": False,
    }
    assert {
        status["name"]: status["explicit_permission"]
        for status in cast(list[dict[str, object]], report["non_tool_permissions"])
    } == {
        "doom_loop": True,
        "external_directory": True,
    }
    assert report["policy_only_permissions"] == []
    assert report["current_only_permissions"] == []
    assert report["mismatched_permissions"] == []
    assert report["inactive_configured_permissions"] == []


def test_doctor_reports_invalid_policy_config_schema_without_crashing(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    install_policy_config(
        xdg_config_home,
        content='[policies.subagents]\ntask = "bogus"\n',
    )
    write_global_config(tmp_path, REPRESENTATIVE_GLOBAL_PERMISSION)

    report = run_doctor_report(tmp_path, xdg_config_home)

    assert report["policy_config_valid"] is False
    assert report["global_policy_applied"] is None


def test_doctor_flags_when_global_policy_is_not_applied_even_if_subagents_match(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    subagents_policy = dict(SUBAGENT_POLICY_EFFECTIVE)
    install_policy_config(
        xdg_config_home,
        content=build_policy_config(
            global_policy={
                "task": "allow",
                "question": "allow",
                "submit_plan": "allow",
                "plannotator_review": "allow",
                "plannotator_annotate": "allow",
                "external_directory": "ask",
                "doom_loop": "ask",
            },
        ),
    )

    with running_tool_server(tool_ids=sorted(subagents_policy), version="1.0.0") as server:
        write_global_payload(
            tmp_path,
            {
                "permission": subagents_policy,
                "server": {
                    "hostname": "127.0.0.1",
                    "port": server.server_port,
                },
            },
        )

        report = run_doctor_report(tmp_path, xdg_config_home)

    assert report["policy_config_valid"] is True
    assert report["global_policy_applied"] is False
    assert cast(dict[str, object], report["server"])["running"] is True
    assert {
        status["name"]: status["explicit_permission"]
        for status in cast(list[dict[str, object]], report["tool_permissions"])
    } == {
        "plannotator_annotate": True,
        "plannotator_review": True,
        "question": True,
        "submit_plan": True,
        "task": True,
    }
    assert {
        status["name"]: status["explicit_permission"]
        for status in cast(list[dict[str, object]], report["non_tool_permissions"])
    } == {
        "doom_loop": True,
        "external_directory": True,
    }
    assert report["inactive_configured_permissions"] == []


def test_doctor_renders_global_policy_differences_explicitly(tmp_path: Path) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    install_policy_config(
        xdg_config_home,
        content=build_policy_config(
            global_policy={
                "read": "allow",
                "task": "allow",
                "external_directory": "ask",
                "doom_loop": "ask",
            },
        ),
    )

    with running_tool_server(tool_ids=["read", "task", "question"], version="2.0.0") as server:
        write_global_payload(
            tmp_path,
            {
                "permission": {
                    "read": "allow",
                    "question": "allow",
                    "external_directory": {
                        "*": "ask",
                        "/tmp/*": "allow",
                    },
                },
                "server": {
                    "hostname": "127.0.0.1",
                    "port": server.server_port,
                },
            },
        )

        report = run_doctor_report(tmp_path, xdg_config_home)

    assert report["global_policy_applied"] is False
    assert report["policy_only_permissions"] == []
    assert report["current_only_permissions"] == ["external_directory", "question", "read"]
    assert report["mismatched_permissions"] == []


def test_doctor_includes_configured_mcp_tools_in_active_tool_inventory(tmp_path: Path) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    install_policy_config(
        xdg_config_home,
        content=build_policy_config(
            global_policy={
                "read": "allow",
                "cut-copy-paste-mcp_copy_lines": "allow",
                "external_directory": "ask",
                "doom_loop": "ask",
            },
            mcps=["cut-copy-paste-mcp"],
        ),
    )
    with running_tool_server(tool_ids=["read"], version="1.2.3") as server:
        write_global_payload(
            tmp_path,
            {
                "permission": compute_minimal_global_permissions_for_test(
                    {
                        "read": "allow",
                        "cut-copy-paste-mcp_copy_lines": "allow",
                        "external_directory": "ask",
                        "doom_loop": "ask",
                    }
                ),
                "server": {
                    "hostname": "127.0.0.1",
                    "port": server.server_port,
                },
                "mcp": {
                    "cut-copy-paste-mcp": {
                        "type": "local",
                        "command": ["npx", "-y", "@fastmcp-me/cut-copy-paste-mcp"],
                    },
                },
            },
        )

        report = run_doctor_report(tmp_path, xdg_config_home)

    assert cast(dict[str, object], report["server"])["running"] is True
    assert report["global_policy_applied"] is True
    active_tools = {
        status["name"]: status["explicit_permission"]
        for status in cast(list[dict[str, object]], report["tool_permissions"])
    }
    assert active_tools["read"] is True
    assert active_tools["cut-copy-paste-mcp_copy_lines"] is True
    assert active_tools["cut-copy-paste-mcp_show_clipboard"] is False
    assert "cut-copy-paste-mcp_copy_lines" not in cast(
        list[str], report["inactive_configured_permissions"]
    )


def test_doctor_flags_cli_global_permissions_that_do_not_correspond_to_known_active_tools(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"
    install_policy_config(
        xdg_config_home,
        content=build_policy_config(
            global_policy={
                "read": "allow",
                "imaginary_tool": "allow",
                "external_directory": "ask",
                "doom_loop": "ask",
            },
        ),
    )

    with running_tool_server(tool_ids=["read"], version="3.0.0") as server:
        write_global_payload(
            tmp_path,
            {
                "permission": compute_minimal_global_permissions_for_test(
                    {
                        "read": "allow",
                        "imaginary_tool": "allow",
                        "external_directory": "ask",
                        "doom_loop": "ask",
                    }
                ),
                "server": {
                    "hostname": "127.0.0.1",
                    "port": server.server_port,
                },
            },
        )

        report = run_doctor_report(tmp_path, xdg_config_home)
        result = run_cli("", "doctor", home=tmp_path, xdg_config_home=xdg_config_home)

    assert cast(dict[str, object], report["server"])["running"] is True
    assert report["global_policy_applied"] is True
    assert report["inactive_configured_permissions"] == ["imaginary_tool"]
    assert "These permissions are present in policies.global but were not found" in result.stdout


def test_install_config_creates_xdg_policy_config_from_live_tool_inventory_and_mcps(
    tmp_path: Path,
) -> None:
    xdg_config_home = tmp_path / "xdg-config"

    with running_tool_server(tool_ids=["read", "task"], version="7.7.7") as server:
        write_global_payload(
            tmp_path,
            {
                "permission": {"read": "allow"},
                "server": {
                    "hostname": "127.0.0.1",
                    "port": server.server_port,
                },
                "mcp": {
                    "cut-copy-paste-mcp": {
                        "type": "local",
                        "command": ["npx", "-y", "@fastmcp-me/cut-copy-paste-mcp"],
                    },
                },
            },
        )

        result = run_cli("", "install-config", home=tmp_path, xdg_config_home=xdg_config_home)

    assert result.returncode == 0, result.stderr
    installed_path = xdg_config_home / "opencode-permission-policy-compiler" / "config.toml"
    assert Path(result.stdout.strip()) == installed_path

    raw_config = installed_path.read_text(encoding="utf-8")
    parsed = cast(dict[str, object], tomllib.loads(raw_config))
    mcps = cast(dict[str, object], parsed["mcps"])
    policies = cast(dict[str, object], parsed["policies"])
    global_policy = cast(dict[str, object], policies["global"])

    assert mcps["servers"] == ["cut-copy-paste-mcp"]
    assert global_policy["read"] == "allow"
    assert global_policy["task"] == "allow"
    assert global_policy["cut-copy-paste-mcp_copy_lines"] == "allow"
    assert global_policy["external_directory"] == "ask"
    assert global_policy["doom_loop"] == "ask"
    assert "# [policies.global.read]" in raw_config
    assert "# [policies.global.external_directory]" in raw_config
