from __future__ import annotations

import re
import subprocess
import sys
from os import environ
from pathlib import Path
from typing import cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTMATTER_PATTERN = re.compile(
    r"\A---\n(?P<frontmatter>.*?)\n---\n(?P<body>[\s\S]*)\Z",
    re.DOTALL,
)


def run_cli(
    markdown_text: str,
    *args: str,
    home: Path,
) -> subprocess.CompletedProcess[str]:
    env = {
        "HOME": str(home),
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }
    if "PATH" in environ:
        env["PATH"] = environ["PATH"]
    return subprocess.run(
        [sys.executable, "-m", "opencode_permission_policy_compiler", *args],
        input=markdown_text,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        env=env,
        check=False,
    )


def parse_output(markdown_text: str) -> tuple[dict[str, object], str]:
    match = FRONTMATTER_PATTERN.match(markdown_text)
    assert match is not None, markdown_text
    raw_metadata = yaml.safe_load(match.group("frontmatter"))
    assert isinstance(raw_metadata, dict)
    metadata = cast(dict[str, object], raw_metadata)
    return metadata, match.group("body")


def write_global_config(tmp_path: Path, contents: str) -> Path:
    config_path = tmp_path / ".config" / "opencode" / "opencode.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(contents.strip() + "\n", encoding="utf-8")
    return config_path


def test_cli_compiles_minimal_overlay_from_standard_global_config(tmp_path: Path) -> None:
    write_global_config(
        tmp_path,
        """
{
  "permission": {
    "webfetch": "allow",
    "bash": {
      "*": "ask",
      "git *": "allow"
    }
  }
}
""",
    )
    source = """---
description: Review code without edits
mode: subagent
policies:
  - review
  - git-inspect
---
Only analyze code and report issues.
"""

    result = run_cli(source, home=tmp_path)

    assert result.returncode == 0, result.stderr
    metadata, body = parse_output(result.stdout)
    assert "policies" not in metadata
    assert metadata["permission"] == {
        "edit": "deny",
        "webfetch": "deny",
        "websearch": "deny",
        "bash": {
            "git diff *": "allow",
            "git log *": "allow",
            "git status *": "allow",
        },
    }
    assert body == "Only analyze code and report issues.\n"


def test_cli_applies_later_policy_override_against_global_baseline(tmp_path: Path) -> None:
    write_global_config(
        tmp_path,
        """
{
  "permission": {
    "bash": "allow",
    "webfetch": "allow"
  }
}
""",
    )
    source = """---
description: Disable web and restrict bash
mode: subagent
policies:
  - bash-unrestricted
  - no-web
---
Do not use the web.
"""

    result = run_cli(source, home=tmp_path)

    assert result.returncode == 0, result.stderr
    metadata, body = parse_output(result.stdout)
    assert metadata["permission"] == {
        "webfetch": "deny",
        "websearch": "deny",
    }
    assert body == "Do not use the web.\n"


def test_cli_omits_permission_when_policy_matches_global_config(tmp_path: Path) -> None:
    write_global_config(
        tmp_path,
        """
{
  "permission": {
    "webfetch": "deny",
    "websearch": "deny"
  }
}
""",
    )
    source = """---
description: Disable web
mode: subagent
policies:
  - no-web
---
No web access.
"""

    result = run_cli(source, home=tmp_path)

    assert result.returncode == 0, result.stderr
    metadata, body = parse_output(result.stdout)
    assert "permission" not in metadata
    assert body == "No web access.\n"


def test_cli_reports_unknown_policy(tmp_path: Path) -> None:
    write_global_config(
        tmp_path,
        """
{
  "permission": {
    "bash": "allow"
  }
}
""",
    )
    source = """---
description: Unknown policy example
mode: subagent
policies:
  - missing-policy
---
Body.
"""

    result = run_cli(source, home=tmp_path)

    assert result.returncode != 0
    assert "Unknown policy" in result.stderr or "Unknown policy" in result.stdout


def test_cli_requires_standard_global_config(tmp_path: Path) -> None:
    source = """---
description: Missing config example
mode: subagent
policies:
  - no-web
---
Body.
"""

    result = run_cli(source, home=tmp_path)

    assert result.returncode != 0
    assert "Standard OpenCode global config does not exist" in (result.stderr or result.stdout)
