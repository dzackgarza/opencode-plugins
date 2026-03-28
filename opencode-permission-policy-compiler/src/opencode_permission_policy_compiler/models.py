from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, RootModel

type PermissionAction = Literal["allow", "ask", "deny"]
type PermissionRule = PermissionAction | dict[str, PermissionAction]
type PermissionFragmentData = dict[str, PermissionRule]


class ConfigDocument(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    permission: RootModel[PermissionFragmentData] | None = None

    def resolved_permission(self) -> dict[str, PermissionRule]:
        if self.permission is None:
            return {}
        return {key: _clone_rule(value) for key, value in self.permission.root.items()}


def _clone_rule(rule: PermissionRule) -> PermissionRule:
    if isinstance(rule, str):
        return rule
    return dict(rule)
