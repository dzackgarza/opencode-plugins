"""Improved Jules CLI - Streamlined workflow."""

from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from improved_jules_cli.api import JulesAPI
from improved_jules_cli.polling import watch_session
from improved_jules_cli.config import (
    get_api_key,
    set_api_key,
    ConfigError,
    get_prompt_template,
    set_prompt_template_path,
    load_config,
)

app = typer.Typer(name="jules-cli")
console = Console()

TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}


def get_client() -> JulesAPI:
    try:
        return JulesAPI(get_api_key())
    except ConfigError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def create(prompt: str):
    """Create a session that creates a PR (plans auto-approved)."""
    client = get_client()

    # Prepend standardized prompt template if configured
    try:
        template = get_prompt_template()
        if template:
            prompt = f"{template}\n\n---\n\n{prompt}"
    except ConfigError as e:
        console.print(f"[yellow]Warning:[/yellow] {e}")

    session = client.create_session(
        prompt=prompt,
        require_plan_approval=False,
        automation_mode="AUTO_CREATE_PR",
    )

    console.print(f"[green]Session:[/green] {session.get('id')}")
    console.print(f"[cyan]URL:[/cyan] {session.get('url')}")


@app.command()
def watch(session_id: str, timeout: Optional[int] = None):
    """Poll until session completes."""
    console.print(f"Watching {session_id}...")
    result = watch_session(get_client(), session_id, interval=5, timeout=timeout)
    state = result.get("state")
    color = "green" if state == "COMPLETED" else "red"
    console.print(f"[{color}]{state}[/{color}]")


@app.command()
def pr(session_id: str):
    """Get PR URL from completed session."""
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

    console.print("[yellow]No PR found[/yellow]")


@app.command()
def re_prompt(session_id: str, feedback: str):
    """Send feedback to session for more work."""
    client = get_client()
    client.send_message(session_id, feedback)
    console.print(f"[green]Feedback sent to {session_id}[/green]")


@app.command()
def delete(session_id: str):
    """Delete a session."""
    client = get_client()
    client.delete_session(session_id)
    console.print(f"[green]Deleted {session_id}[/green]")


@app.command()
def list(limit: int = 20):
    """List recent sessions."""
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
    state = session.get("state", "UNKNOWN")
    color = (
        "green" if state == "COMPLETED" else "red" if state == "FAILED" else "yellow"
    )
    console.print(f"[{color}]{state}[/{color}]")


# Config commands (minimal)
@app.command()
def config_show():
    """Show configuration."""
    try:
        get_api_key()
    except ConfigError:
        console.print("[red]API key not set[/red]")

    cfg = load_config()
    template = cfg.get("prompt_template_path", "(not set)")
    console.print(f"Prompt template: {template}")


@app.command()
def config_set_prompt_template(path: str):
    """Set standardized prompt template file."""
    set_prompt_template_path(path)
    console.print(f"[green]Prompt template:[/green] {path}")


@app.command()
def config_set_api_key(key: str):
    """Set API key."""
    set_api_key(key)
    console.print("[green]API key saved[/green]")


if __name__ == "__main__":
    app()
