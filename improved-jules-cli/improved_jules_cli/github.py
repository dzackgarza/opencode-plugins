"""Improved Jules CLI - GitHub issue fetching."""

import re
import subprocess
from typing import Tuple


def parse_issue_url(url: str) -> Tuple[str, str, int]:
    """Parse GitHub issue URL into owner, repo, and issue number.

    Examples:
        https://github.com/owner/repo/issues/123
        https://github.com/owner/repo/issues/123#issuecomment-456
    """
    # Match GitHub issue URLs
    pattern = r"github\.com/([^/]+)/([^/]+)/issues/(\d+)"
    match = re.search(pattern, url)
    if not match:
        raise ValueError(f"Invalid GitHub issue URL: {url}")

    owner = match.group(1)
    repo = match.group(2)
    issue_number = int(match.group(3))

    return owner, repo, issue_number


def fetch_issue_markdown(owner: str, repo: str, issue_number: int) -> str:
    """Fetch issue and comments, assemble into markdown."""
    lines = []

    # Fetch issue
    result = subprocess.run(
        [
            "gh",
            "issue",
            "view",
            str(issue_number),
            "--repo",
            f"{owner}/{repo}",
            "--json",
            "title,body,author,createdAt,labels",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to fetch issue #{issue_number}: {result.stderr}")

    import json

    issue = json.loads(result.stdout)

    # Title
    lines.append(f"# Issue #{issue_number}: {issue.get('title', '')}")
    lines.append("")

    # Labels
    labels = issue.get("labels", [])
    if labels:
        label_names = [l.get("name", "") for l in labels]
        lines.append(f"**Labels:** {', '.join(label_names)}")
        lines.append("")

    # Author
    author = issue.get("author", {})
    if author:
        lines.append(f"**Author:** {author.get('login', 'unknown')}")
    lines.append(f"**Created:** {issue.get('createdAt', '')}")
    lines.append("")

    # Body
    body = issue.get("body", "")
    if body:
        lines.append("## Description")
        lines.append("")
        lines.append(body)
        lines.append("")

    # Fetch comments
    result = subprocess.run(
        [
            "gh",
            "issue",
            "view",
            str(issue_number),
            "--repo",
            f"{owner}/{repo}",
            "--json",
            "comments",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        data = json.loads(result.stdout)
        comments = data.get("comments", [])

        if comments:
            lines.append("## Comments")
            lines.append("")

            for i, comment in enumerate(comments, 1):
                author = comment.get("author", {})
                author_login = author.get("login", "unknown") if author else "unknown"
                created_at = comment.get("createdAt", "")
                body = comment.get("body", "")

                lines.append(f"### Comment {i}")
                lines.append("")
                lines.append(f"**{author_login}** at {created_at}:")
                lines.append("")
                lines.append(body)
                lines.append("")

    # Footer with issue URL
    lines.append("---")
    lines.append(f"Issue URL: https://github.com/{owner}/{repo}/issues/{issue_number}")

    return "\n".join(lines)
