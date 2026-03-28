from __future__ import annotations

import re
from collections.abc import Mapping
from typing import cast

import yaml
from pydantic import validate_call

from .errors import MarkdownError

FRONTMATTER_PATTERN = re.compile(
    r"\A---\r?\n(?P<frontmatter>.*?)\r?\n---(?:\r?\n(?P<body>[\s\S]*))?\Z",
    re.DOTALL,
)


@validate_call
def parse_markdown_document(content: str) -> tuple[dict[str, object], str]:
    match = FRONTMATTER_PATTERN.match(content)
    if match is None:
        msg = "Expected markdown with YAML frontmatter delimited by ---"
        raise MarkdownError(msg)

    frontmatter_text = match.group("frontmatter")
    body = match.group("body") or ""

    try:
        raw_metadata: object = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as exc:
        msg = f"Failed to parse YAML frontmatter: {exc}"
        raise MarkdownError(msg) from exc

    if not isinstance(raw_metadata, dict):
        msg = "Markdown frontmatter must parse to a mapping"
        raise MarkdownError(msg)
    metadata = cast(dict[str, object], raw_metadata)

    return metadata, body


@validate_call
def render_markdown_document(metadata: Mapping[str, object], body: str) -> str:
    yaml_text = yaml.safe_dump(
        dict(metadata),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).strip()
    return f"---\n{yaml_text}\n---\n{body}"
