# improved-jules-cli Design

## Overview

A Typer-based Python CLI wrapper around the Jules REST API that extends the official `jules` CLI with additional functionality for session management, polling, and callbacks.

## Problem

The official Jules CLI (`@google/jules`) has limited functionality:

- No way to re-prompt completed sessions
- No polling with callbacks
- No direct API access for advanced use cases
- Limited session state inspection

## API Analysis

### Base URL

```
https://jules.googleapis.com/v1alpha
```

### Authentication

- API key via `x-goog-api-key` header
- Get key from https://jules.google.com/settings

### Key Endpoints

| Endpoint                     | Method | Purpose                        |
| ---------------------------- | ------ | ------------------------------ |
| `/sessions`                  | POST   | Create new session             |
| `/sessions`                  | GET    | List all sessions              |
| `/sessions/{id}`             | GET    | Get session details            |
| `/sessions/{id}`             | DELETE | Delete/cancel session          |
| `/sessions/{id}:sendMessage` | POST   | Send message to active session |
| `/sessions/{id}:approvePlan` | POST   | Approve plan                   |
| `/sessions/{id}/activities`  | GET    | List session activities        |

### Session States

| State                  | Description                   |
| ---------------------- | ----------------------------- |
| QUEUED                 | Waiting to be processed       |
| PLANNING               | Analyzing task, creating plan |
| AWAITING_PLAN_APPROVAL | Waiting for user approval     |
| AWAITING_USER_FEEDBACK | Needs additional input        |
| IN_PROGRESS            | Actively working              |
| PAUSED                 | Session paused                |
| COMPLETED              | Task done successfully        |
| FAILED                 | Task failed                   |

### Activity Types

- `planGenerated` - Plan created
- `planApproved` - Plan approved
- `userMessaged` - Message from user
- `agentMessaged` - Message from Jules
- `progressUpdated` - Status update
- `sessionCompleted` - Success
- `sessionFailed` - Error

## Design

### CLI Commands

```python
# Session management
jules-cli list                      # List all sessions
jules-cli get <session_id>         # Get session details
jules-cli status <session_id>       # Quick status check
jules-cli delete <session_id>       # Cancel/delete session
jules-cli create "<prompt>"          # Create new session
jules-cli send <session_id> "<msg>" # Send message to session

# Polling
jules-cli watch <session_id>        # Poll until complete
jules-cli watch --callback "cmd"    # Run command on complete

# Advanced
jules-cli activities <session_id>   # List activities
jules-cli artifacts <session_id>    # Get code changes
jules-cli re-prompt <session_id> "<feedback>"  # Send follow-up

# Config
jules-cli config set-api-key <key> # Set API key
jules-cli config show              # Show config
```

### Core Modules

```
improved_jules_cli/
├── __init__.py
├── __main__.py          # Entry point
├── api.py                # Raw API client
├── cli.py                # Typer commands
├── config.py             # API key management
├── models.py             # Pydantic models
├── polling.py            # Watch/poll utilities
├── callbacks.py         # Callback execution
└── utils.py              # Helpers
```

### Key Features

1. **API Client** (`api.py`)
   - Thin wrapper around Jules REST API
   - Handles auth, pagination, errors
   - Returns typed responses

2. **Polling** (`polling.py`)
   - `watch_session(session_id, interval=5)` - Poll until terminal state
   - `watch_with_callback(session_id, callback, interval=5)` - Run cmd on complete
   - Configurable poll interval
   - Timeout support

3. **Callbacks** (`callbacks.py`)
   - Execute arbitrary bash commands
   - Pass session data as env vars
   - `JULES_SESSION_ID`, `JULES_STATE`, `JULES_OUTPUT_URL`

4. **Reprompting** - Send messages to ANY session state (including COMPLETED)

### Configuration

- API key stored in `~/.config/improved-jules-cli/config.json`
- Or via `JULES_API_KEY` env var

### Example Usage

```bash
# Watch session and run command on complete
jules-cli watch 15241078297932947933 --callback "echo 'Done!'"

# Re-prompt completed session
jules-cli re-prompt 15241078297932947933 "Actually, also add tests for edge cases"

# List with filters
jules-cli list --state COMPLETED --repo dzackgarza/opencode-plugins
```

## Tasks

1. Set up Python project (pyproject.toml, justfile)
2. Implement API client (`api.py`)
3. Add Pydantic models (`models.py`)
4. Build Typer CLI (`cli.py`)
5. Implement polling (`polling.py`)
6. Add callback system (`callbacks.py`)
7. Add config management (`config.py`)
8. Tests

## Trade-offs

- Using `requests` instead of `httpx` for simplicity
- No async support initially (can add later)
- Local config file vs env var priority
