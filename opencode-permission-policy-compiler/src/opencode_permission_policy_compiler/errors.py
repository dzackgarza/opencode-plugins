from __future__ import annotations


class CompilerError(ValueError):
    """Base error for policy compilation failures."""


class ConfigError(CompilerError):
    """Raised when OpenCode config discovery or parsing fails."""


class MarkdownError(CompilerError):
    """Raised when markdown frontmatter cannot be parsed or transformed."""


class PolicyResolutionError(CompilerError):
    """Raised when requested policies cannot be resolved."""
