"""Improved Jules CLI - Main CLI."""

from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from improved_jules_cli.api import JulesAPI
from improved_jules_cli.polling import watch_session, watch_with_callback
from improved_jules_cli.config import (
    get_api_key,
    set_api_key,
    ConfigError,
    get_prompt_template,
    set_prompt_template_path,
    set_branch_prefix,
)

app = typer.Typer(
    name="jules-cli", help="Improved Jules CLI with polling and callbacks"
)
console = Console()

TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}


def get_client() -> JulesAPI:
    """Get API client."""
    try:
        return JulesAPI(get_api_key())
    except ConfigError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def list(
    state: Optional[str] = typer.Option(None, help="Filter by state"),
    repo: Optional[str] = typer.Option(None, help="Filter by repo (partial match)"),
    limit: int = typer.Option(30, help="Max results"),
):
    """List all sessions."""
    client = get_client()

    all_sessions = []
    page_token = None

    while len(all_sessions) < limit:
        resp = client.list_sessions(
            page_size=min(100, limit - len(all_sessions)), page_token=page_token
        )
        sessions = resp.get("sessions", [])
        if not sessions:
            break
        all_sessions.extend(sessions)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    # Filter
    if state:
        all_sessions = [s for s in all_sessions if s.get("state") == state.upper()]
    if repo:
        # Extract repo from source context if available
        all_sessions = [
            s
            for s in all_sessions
            if repo.lower() in str(s.get("sourceContext", "")).lower()
        ]

    table = Table(title="Jules Sessions")
    table.add_column("ID", style="cyan")
    table.add_column("State", style="yellow")
    table.add_column("Title")
    table.add_column("Created")

    for s in all_sessions[:limit]:
        table.add_row(
            s.get("id", ""),
            s.get("state", ""),
            s.get("title", s.get("prompt", "")[:50]),
            s.get("createTime", "")[:10],
        )

    console.print(table)


@app.command()
def sources():
    """List available sources (repos)."""
    client = get_client()
    resp = client.list_sources()
    sources = resp.get("sources", [])

    if not sources:
        console.print("[yellow]No sources found[/yellow]")
        return

    table = Table(title="Jules Sources")
    table.add_column("ID", style="cyan")
    table.add_column("Owner", style="yellow")
    table.add_column("Repo", style="yellow")
    table.add_column("Default Branch")

    for s in sources:
        gh = s.get("githubRepo", {})
        table.add_row(
            s.get("id", ""),
            gh.get("owner", ""),
            gh.get("repo", ""),
            gh.get("defaultBranch", {}).get("displayName", ""),
        )

    console.print(table)


@app.command()
def get(session_id: str):
    """Get session details."""
    client = get_client()
    session = client.get_session(session_id)

    console.print(f"[cyan]ID:[/cyan] {session.get('id')}")
    console.print(f"[cyan]State:[/cyan] {session.get('state')}")
    console.print(f"[cyan]Title:[/cyan] {session.get('title')}")
    console.print(f"[cyan]Prompt:[/cyan] {session.get('prompt')}")
    console.print(f"[cyan]URL:[/cyan] {session.get('url')}")
    console.print(f"[cyan]Created:[/cyan] {session.get('createTime')}")
    console.print(f"[cyan]Updated:[/cyan] {session.get('updateTime')}")

    if "outputs" in session:
        console.print("[cyan]Outputs:[/cyan]")
        for out in session.get("outputs", []):
            if "pullRequest" in out:
                pr = out["pullRequest"]
                console.print(f"  PR: {pr.get('url')}")


@app.command()
def status(session_id: str):
    """Quick status check."""
    client = get_client()
    session = client.get_session(session_id)
    state = session.get("state", "UNKNOWN")

    color = (
        "green" if state == "COMPLETED" else "red" if state == "FAILED" else "yellow"
    )
    console.print(f"[{color}]{state}[/{color}]")


@app.command()
def delete(session_id: str):
    """Delete/cancel a session."""
    client = get_client()
    client.delete_session(session_id)
    console.print(f"[green]Session {session_id} deleted[/green]")


@app.command()
def create(
    prompt: str,
    title: Optional[str] = typer.Option(None, help="Session title"),
    auto_pr: bool = typer.Option(False, help="Auto-create PR"),
):
    """Create a new session (plans are auto-approved).

    Note: Source/repo is configured in Jules dashboard.
    """
    client = get_client()

    # Prepend prompt template if configured
    try:
        template = get_prompt_template()
        if template:
            prompt = f"{template}\n\n---\n\n{prompt}"
    except ConfigError as e:
        console.print(f"[yellow]Warning:[/yellow] {e}")

    session = client.create_session(
        prompt=prompt,
        title=title,
        require_plan_approval=False,
        automation_mode="AUTO_CREATE_PR" if auto_pr else None,
    )

    session_id = session.get("id")
    console.print(f"[green]Session created:[/green] {session_id}")
    console.print(f"URL: {session.get('url')}")


@app.command()
def send(session_id: str, message: str):
    """Send a message to a session."""
    client = get_client()
    client.send_message(session_id, message)
    console.print(f"[green]Message sent to {session_id}[/green]")


@app.command()
def re_prompt(session_id: str, feedback: str):
    """Re-prompt a completed or active session with feedback."""
    client = get_client()
    session = client.get_session(session_id)
    state = session.get("state")

    # Can send to any state except some terminal ones
    if state in TERMINAL_STATES and state != "COMPLETED":
        console.print(f"[yellow]Warning:[/yellow] Session is {state}. Sending anyway.")

    client.send_message(session_id, feedback)
    console.print(f"[green]Re-prompt sent to {session_id}[/green]")


@app.command()
def watch(
    session_id: str,
    interval: int = typer.Option(5, help="Poll interval seconds"),
    timeout: Optional[int] = typer.Option(None, help="Timeout seconds"),
):
    """Watch a session until complete."""
    console.print(f"Watching {session_id}...")

    result = watch_session(get_client(), session_id, interval=interval, timeout=timeout)

    state = result.get("state")
    color = "green" if state == "COMPLETED" else "red"
    console.print(f"[{color}]Session {state}[/{color}]")


@app.command()
def watch_callback(
    session_id: str,
    callback: str,
    interval: int = typer.Option(5, help="Poll interval seconds"),
    timeout: Optional[int] = typer.Option(None, help="Timeout seconds"),
):
    """Watch session and run callback on complete."""
    console.print(f"Watching {session_id}, will run: {callback}")

    result = watch_with_callback(
        get_client(), session_id, callback, interval=interval, timeout=timeout
    )

    console.print("[green]Callback executed[/green]")


@app.command()
def activities(session_id: str, limit: int = 20):
    """List session activities."""
    client = get_client()

    all_activities = []
    page_token = None

    while len(all_activities) < limit:
        resp = client.list_activities(
            session_id,
            page_size=min(100, limit - len(all_activities)),
            page_token=page_token,
        )
        activities = resp.get("activities", [])
        if not activities:
            break
        all_activities.extend(activities)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    table = Table(title=f"Activities for {session_id}")
    table.add_column("Time")
    table.add_column("Type")
    table.add_column("Description")

    for a in all_activities[:limit]:
        # Determine type
        a_type = "UNKNOWN"
        for t in [
            "planGenerated",
            "planApproved",
            "userMessaged",
            "agentMessaged",
            "progressUpdated",
            "sessionCompleted",
            "sessionFailed",
        ]:
            if t in a:
                a_type = t
                break

        table.add_row(a.get("createTime", "")[:19], a_type, a.get("description", ""))

    console.print(table)


@app.command()
def config_set_api_key(key: str):
    """Set API key."""
    set_api_key(key)
    console.print("[green]API key saved[/green]")


@app.command()
def config_show():
    """Show configuration."""
    try:
        key = get_api_key()
        console.print(f"API key: {key[:10]}..." if len(key) > 10 else key)
    except ConfigError as e:
        console.print(f"[red]Error:[/red] {e}")

    # Show prompt template path
    config = load_config()
    template_path = config.get("prompt_template_path")
    if template_path:
        console.print(f"Prompt template: {template_path}")
    else:
        console.print("Prompt template: (not set)")

    # Show branch prefix
    branch_prefix = config.get("branch_prefix")
    if branch_prefix:
        console.print(f"Branch prefix: {branch_prefix}")
    else:
        console.print("Branch prefix: (not set)")


def load_config() -> dict:
    """Load config (helper for config_show)."""
    import json
    from pathlib import Path

    CONFIG_FILE = Path.home() / ".config" / "improved-jules-cli" / "config.json"
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text())
    except json.JSONDecodeError:
        return {}


@app.command()
def config_set_prompt_template(path: str):
    """Set prompt template file path."""
    set_prompt_template_path(path)
    console.print(f"[green]Prompt template path set to:[/green] {path}")


@app.command()
def config_set_branch_prefix(prefix: str):
    """Set branch prefix for new sessions."""
    set_branch_prefix(prefix)
    console.print(f"[green]Branch prefix set to:[/green] {prefix}")


if __name__ == "__main__":
    app()
