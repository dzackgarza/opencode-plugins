"""Whitelist framework-driven symbols for vulture."""

from opencode_permission_policy_compiler.cli import compile_agent
from opencode_permission_policy_compiler.models import ConfigDocument

_ = compile_agent

_ = ConfigDocument.model_config
