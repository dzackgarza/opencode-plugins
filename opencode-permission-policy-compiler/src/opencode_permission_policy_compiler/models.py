from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

type PermissionAction = Literal["allow", "ask", "deny"]
type PermissionRule = PermissionAction | dict[str, PermissionAction]
type PermissionFragmentData = dict[str, PermissionRule]


class McpLocalServerDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    type: Literal["local"]
    command: list[str]
    environment: dict[str, str] | None = None
    enabled: bool | None = None
    timeout: int | None = None


class McpOAuthDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    clientId: str | None = None
    clientSecret: str | None = None
    scope: str | None = None


class McpRemoteServerDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    type: Literal["remote"]
    url: str
    enabled: bool | None = None
    headers: dict[str, str] | None = None
    oauth: McpOAuthDocument | Literal[False] | None = None
    timeout: int | None = None


class McpDisabledServerDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    enabled: Literal[False]


type McpServerDocument = (
    McpLocalServerDocument | McpRemoteServerDocument | McpDisabledServerDocument
)


class ConfigDocument(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    permission: RootModel[PermissionFragmentData] | None = None
    server: ServerDocument | None = None
    mcp: dict[str, McpServerDocument] | None = None

    def resolved_permission(self) -> dict[str, PermissionRule]:
        if self.permission is None:
            return {}
        return {key: _clone_rule(value) for key, value in self.permission.root.items()}

    def resolved_mcp(self) -> dict[str, McpServerDocument]:
        return dict(self.mcp or {})

    def server_base_urls(self) -> list[str]:
        port = 4096
        if self.server is not None and self.server.port is not None:
            port = self.server.port

        hostname = "127.0.0.1"
        if self.server is not None and self.server.hostname:
            hostname = self.server.hostname

        candidates: list[str] = []
        for host in _server_host_candidates(hostname):
            url = f"http://{host}:{port}"
            if url not in candidates:
                candidates.append(url)
        return candidates


class ServerDocument(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    port: int | None = None
    hostname: str | None = None


class ServerHealthDocument(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    healthy: Literal[True]
    version: str


class ToolIDsDocument(RootModel[list[str]]):
    model_config = ConfigDict(strict=True)


class McpsConfigDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    servers: list[str] = Field(default_factory=list)


class PolicyCatalogDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    mcps: McpsConfigDocument = Field(default_factory=McpsConfigDocument)
    policies: dict[str, RootModel[PermissionFragmentData]]

    def resolved_policies(self) -> dict[str, PermissionFragmentData]:
        return {
            name: {key: _clone_rule(value) for key, value in fragment.root.items()}
            for name, fragment in self.policies.items()
        }

    def configured_mcp_servers(self) -> list[str]:
        return list(self.mcps.servers)

    def resolved_global_policy(self) -> PermissionFragmentData | None:
        policy = self.policies.get("global")
        if policy is None:
            return None
        return {key: _clone_rule(value) for key, value in policy.root.items()}


class ToolPermissionStatus(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str
    explicit_permission: bool


class NonToolPermissionStatus(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str
    explicit_permission: bool


class PermissionMismatchStatus(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str
    policy_value: PermissionRule
    current_value: PermissionRule


class ServerStatusDocument(BaseModel):
    model_config = ConfigDict(strict=True)

    running: bool
    base_url: str | None = None
    version: str | None = None


class DoctorInputDocument(BaseModel):
    model_config = ConfigDict(strict=True)

    policy_config_path: Path
    global_config_path: Path
    global_policy_permissions: dict[str, PermissionRule] | None = None
    current_permissions: dict[str, PermissionRule] | None = None
    known_policies: dict[str, PermissionFragmentData] | None = None
    policy_config_error: str | None = None
    global_config_error: str | None = None
    server_base_urls: list[str] = Field(default_factory=list)
    configured_mcp_servers: list[str] = Field(default_factory=list)
    mcp_servers: dict[str, McpServerDocument] | None = None


class DoctorReportDocument(BaseModel):
    model_config = ConfigDict(strict=True)

    policy_config_path: Path
    policy_config_valid: bool
    policy_config_error: str | None = None
    global_config_path: Path
    global_config_valid: bool
    global_config_error: str | None = None
    global_policy_applied: bool | None = None
    global_policy_application_error: str | None = None
    server: ServerStatusDocument
    tool_permissions: list[ToolPermissionStatus] = Field(default_factory=list)
    non_tool_permissions: list[NonToolPermissionStatus] = Field(default_factory=list)
    policy_only_permissions: list[str] = Field(default_factory=list)
    current_only_permissions: list[str] = Field(default_factory=list)
    mismatched_permissions: list[PermissionMismatchStatus] = Field(default_factory=list)
    tool_scan_error: str | None = None
    inactive_configured_permissions: list[str] = Field(default_factory=list)

    def has_errors(self) -> bool:
        return (
            not self.policy_config_valid
            or not self.global_config_valid
            or self.global_policy_applied is False
            or self.tool_scan_error is not None
            or bool(self.inactive_configured_permissions)
        )


def _clone_rule(rule: PermissionRule) -> PermissionRule:
    if isinstance(rule, str):
        return rule
    return dict(rule)


def _server_host_candidates(hostname: str) -> list[str]:
    if hostname in {"0.0.0.0", "::", "::0", "::1"}:
        return ["127.0.0.1", "localhost"]
    if hostname == "127.0.0.1":
        return ["127.0.0.1", "localhost"]
    if hostname == "localhost":
        return ["localhost", "127.0.0.1"]
    return [hostname]
