from __future__ import annotations

import sys

from cyclopts import App
from pydantic import validate_call

from .config import load_global_permission_base
from .errors import CompilerError
from .logic import compile_markdown_agent

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
    sys.stdout.write(compile_markdown_agent(source, base_permissions))


def main() -> None:
    try:
        app()
    except CompilerError as exc:
        raise SystemExit(str(exc)) from exc
