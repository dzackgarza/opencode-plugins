"""Improved Jules CLI - Polling utilities."""

import subprocess
import time
from typing import Optional
import os

TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED", "PAUSED"}


def watch_session(
    client, session_id: str, interval: int = 5, timeout: Optional[int] = None
) -> dict:
    """Watch a session until it reaches a terminal state.

    Args:
        client: JulesAPI client
        session_id: Session to watch
        interval: Poll interval in seconds
        timeout: Optional timeout in seconds

    Returns:
        Final session state dict
    """
    start_time = time.time()

    while True:
        session = client.get_session(session_id)
        state = session.get("state")

        if state in TERMINAL_STATES:
            return session

        if timeout and (time.time() - start_time) > timeout:
            raise TimeoutError(f"Session did not complete within {timeout}s")

        time.sleep(interval)


def watch_with_callback(
    client,
    session_id: str,
    callback: str,
    interval: int = 5,
    timeout: Optional[int] = None,
) -> dict:
    """Watch a session and execute callback when complete.

    Args:
        client: JulesAPI client
        session_id: Session to watch
        callback: Bash command to execute on completion
        interval: Poll interval in seconds
        timeout: Optional timeout in seconds

    Returns:
        Final session state dict
    """
    # First watch until complete
    session = watch_session(client, session_id, interval=interval, timeout=timeout)

    # Set environment variables for callback
    env = os.environ.copy()
    env["JULES_SESSION_ID"] = session_id
    env["JULES_STATE"] = session.get("state", "")
    env["JULES_URL"] = session.get("url", "")

    # Get outputs if any
    outputs = session.get("outputs", [])
    if outputs and "pullRequest" in outputs[0]:
        pr = outputs[0].get("pullRequest", {})
        env["JULES_PR_URL"] = pr.get("url", "")
        env["JULES_PR_TITLE"] = pr.get("title", "")

    # Execute callback
    result = subprocess.run(
        callback, shell=True, env=env, capture_output=True, text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Callback failed: {result.stderr}")

    return session
