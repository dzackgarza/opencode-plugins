"""Improved Jules CLI - Streamlined workflow."""

import typer
from rich.console import Console
from rich.table import Table

from improved_jules_cli.api import JulesAPI
from improved_jules_cli.config import (
    get_api_key,
    set_api_key,
    ConfigError,
    get_prompt_template,
    set_prompt_slug,
    load_config,
)
from improved_jules_cli.github import fetch_issue_markdown, parse_issue_url

app = typer.Typer(name="jules-cli")
console = Console()

TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}


@app.command()
def help():
    """Show workflow documentation."""
    console.print("""
[bold]Jules CLI - Workflow[/bold]

[bold]IMPORTANT: Prompt Writing - READ THIS FIRST[/bold]
Jules has ONLY access to exactly what exists in the target repository.
- It CANNOT read external files, standards docs, or data outside the repo
- If you reference something not in the repo (e.g., "read README_STANDARDS.md"),
  that part of the task will be SILENTLY IGNORED
- Jules will goal-substitute: produce trivial checkbox work to look complete
  without actually addressing the real requirements
- ALWAYS paste required standards, requirements, or context DIRECTLY into the prompt

[green]1. Create[/green]
    jules-cli create --repo owner/repo --issue 123
    → Fetches issue #123, uses title+body+comments as prompt

[bold]Required: --repo[/bold]
    Jules needs to know which repository to work on.
    Format: owner/repo (e.g., dzackgarza/opencode-zotero-plugin)
    The repo must be connected to Jules (see Jules dashboard).

[green]2. Wait[/green]
    jules-cli watch 123         # Check status once
    jules-cli watch-callback 123 "callback.sh"
    → Polls until done, runs callback with env vars:
      JULES_SESSION_ID, JULES_STATE, JULES_URL, JULES_PR_URL
    jules-cli list             # List all sessions

[green]3. Get PR[/green]
    jules-cli pr 123
    → Returns PR URL or pending changeset

[green]4. Review[/green]
    → Check PR at JULES_PR_URL
    → If issues found:

[green]5. Feedback[/green]
    jules-cli feedback 123 "Review says: fix the tests"
    → Feeds back to agent for more work

[green]6. Clean up[/green]
    jules-cli delete 123
    → Removes session when done

[bold]Prompt Template[/bold]
    A standardized template can be prepended to every prompt.
    Configure with: jules-cli config-set-prompt-slug <slug>
""")


def get_client() -> JulesAPI:
    try:
        return JulesAPI(get_api_key())
    except ConfigError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def create(
    issue_url: str = typer.Argument(
        ..., help="GitHub issue URL (e.g., https://github.com/owner/repo/issues/123)"
    ),
    branch: str = typer.Option("main", "--branch", "-b", help="Branch to work on"),
    context: list[str] = typer.Option(
        [],
        "--context",
        "-c",
        help="Additional files to include as context (will be inlined into prompt)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Just print what would be sent to Jules without creating a session",
    ),
):
    """Create a session from a GitHub issue that creates a PR (plans auto-approved).

    Pass a GitHub issue URL (e.g., https://github.com/owner/repo/issues/123).
    Use --context to attach additional files (e.g., --context README_STANDARDS.md).
    """
    # Parse issue URL
    try:
        owner, repo_name, issue_number = parse_issue_url(issue_url)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Dry run - fetch issue and print prompt without needing Jules auth
    if dry_run:
        console.print("[yellow]=== DRY RUN ===[/yellow]")
        console.print(f"[cyan]Repo:[/cyan] {owner}/{repo_name}")
        console.print(f"[cyan]Issue URL:[/cyan] {issue_url}")
        console.print(f"[cyan]Branch:[/cyan] {branch or 'main'}")
        if context:
            console.print(f"[cyan]Context files:[/cyan] {', '.join(context)}")

        # Fetch issue
        console.print("[cyan]Fetching issue...[/cyan]")
        try:
            prompt = fetch_issue_markdown(owner, repo_name, issue_number)
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        # Build prompt
        try:
            template = get_prompt_template(
                prompt, context_files=context if context else None
            )
            if template:
                prompt = f"{template}\n\n---\n\nTask:\n\n{prompt}"
        except ConfigError as e:
            console.print(f"[yellow]Warning:[/yellow] {e}")

        console.print()
        console.print("[cyan]Prompt:[/cyan]")
        console.print(prompt)
        raise typer.Exit(0)

    # Full create - need Jules auth
    client = get_client()

    # Look up the source
    source = client.find_source_by_repo(owner, repo_name)
    if not source:
        console.print(
            f"[red]Error:[/red] Repo '{owner}/{repo_name}' not connected to Jules. Run 'jules remote list --repo' to see connected repos."
        )
        raise typer.Exit(1)

    source_id = source["name"]
    default_branch = source["githubRepo"]["defaultBranch"]["displayName"]

    # Use provided branch or default
    starting_branch = branch if branch else default_branch

    # Fetch issue and assemble into prompt
    console.print(f"[cyan]Fetching issue from {owner}/{repo_name}...[/cyan]")
    try:
        prompt = fetch_issue_markdown(owner, repo_name, issue_number)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Prepend standardized prompt template if configured
    try:
        template = get_prompt_template(
            prompt, context_files=context if context else None
        )
        if template:
            prompt = f"{template}\n\n---\n\nTask:\n\n{prompt}"
    except ConfigError as e:
        console.print(f"[yellow]Warning:[/yellow] {e}")

    # Build source context for the repo (API format)
    source_context = {
        "source": source_id,
        "githubRepoContext": {"startingBranch": starting_branch},
    }

    session = client.create_session(
        prompt=prompt,
        source_context=source_context,
        require_plan_approval=False,
        automation_mode="AUTO_CREATE_PR",
    )

    console.print(f"[green]Session:[/green] {session.get('id')}")
    console.print(f"[cyan]URL:[/cyan] {session.get('url')}")


@app.command()
def watch(session_id: str):
    """Check session status once."""
    client = get_client()
    session = client.get_session(session_id)
    state = session.get("state")
    color = (
        "green" if state == "COMPLETED" else "red" if state == "FAILED" else "yellow"
    )
    console.print(f"[{color}]{state}[/{color}]")


@app.command()
def watch_callback(session_id: str, callback: str):
    """Poll until done, then run callback."""
    from improved_jules_cli.polling import watch_with_callback

    result = watch_with_callback(get_client(), session_id, callback, interval=5)
    console.print("[green]Done, callback executed[/green]")


@app.command()
def pr(session_id: str):
    """Get PR URL or changeset from completed session."""
    client = get_client()
    session = client.get_session(session_id)

    outputs = session.get("outputs", [])
    if not outputs:
        console.print("[yellow]No outputs yet[/yellow]")
        return

    for out in outputs:
        if "pullRequest" in out:
            pr = out["pullRequest"]
            console.print(pr.get("url", ""))
            return
        if "changeSet" in out:
            cs = out["changeSet"]
            patch = cs.get("gitPatch", {})
            console.print("[yellow]Changes pending PR:[/yellow]")
            console.print(patch.get("suggestedCommitMessage", ""))
            return

    console.print("[yellow]No PR found[/yellow]")


@app.command()
def feedback(session_id: str, message: str):
    """Send feedback to session for more work."""
    client = get_client()
    client.send_message(session_id, message)
    console.print(f"[green]Feedback sent to {session_id}[/green]")


@app.command()
def delete(session_id: str):
    """Delete a session."""
    client = get_client()
    client.delete_session(session_id)
    console.print(f"[green]Deleted {session_id}[/green]")


@app.command()
def list(limit: int = 20):
    """List all sessions."""
    client = get_client()
    resp = client.list_sessions(page_size=limit)
    sessions = resp.get("sessions", [])

    table = Table(title="Sessions")
    table.add_column("ID", style="cyan")
    table.add_column("State", style="yellow")
    table.add_column("Title")

    for s in sessions:
        table.add_row(
            s.get("id", ""),
            s.get("state", ""),
            (s.get("title") or s.get("prompt", ""))[:60],
        )
    console.print(table)


@app.command()
def status(session_id: str):
    """Quick status check."""
    client = get_client()
    session = client.get_session(session_id)
    state = session.get("state")
    color = (
        "green" if state == "COMPLETED" else "red" if state == "FAILED" else "yellow"
    )
    console.print(f"[{color}]{state}[/{color}]")


@app.command()
def get(session_id: str):
    """Get session details."""
    client = get_client()
    session = client.get_session(session_id)
    console.print(f"[cyan]ID:[/cyan] {session.get('id')}")
    console.print(f"[cyan]State:[/cyan] {session.get('state')}")
    console.print(f"[cyan]Prompt:[/cyan] {session.get('prompt', '')[:500]}...")


# Config commands (hidden - one-time setup only)
@app.command(hidden=True)
def config_show():
    """Show configuration."""
    try:
        get_api_key()
    except ConfigError:
        console.print("[red]API key not set[/red]")

    cfg = load_config()
    slug = cfg.get("prompt_slug", "(not set)")
    path = cfg.get("prompt_template_path", "(not set)")
    console.print(f"Prompt slug: {slug}")
    console.print(f"Prompt file: {path}")


@app.command(hidden=True)
def config_set_prompt_slug(slug: str):
    """Set ai-prompts slug for prompt template."""
    set_prompt_slug(slug)
    console.print(f"[green]Prompt slug:[/green] {slug}")


@app.command(hidden=True)
def config_set_api_key(key: str):
    """Set API key."""
    set_api_key(key)
    console.print("[green]API key saved[/green]")


if __name__ == "__main__":
    app()
