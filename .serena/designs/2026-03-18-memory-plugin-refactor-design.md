# Memory Plugin CLI Extraction

## Problem

`opencode-memory-plugin` currently encapsulates both the MCP server implementation (used by the agent) and the CLI tool, leading to tight coupling and unnecessarily bloated dependencies for users who may only want one part.

## Approach

1.  **Extract CLI**: Create a new repository `memory-manager` and move the CLI logic (`src/opencode_memory/cli`) into it.
2.  **Refactor Plugin**: Strip `opencode-memory-plugin` of its CLI dependencies (`typer`) and the CLI entry point definition in `pyproject.toml`.
3.  **Implement Wrapper**: Modify the plugin to interact with the new CLI using `uvx` (e.g., `uvx git+https://github.com/path/to/memory-manager@main opencode-memory ...`).
4.  **Verify**: Ensure the plugin still functions correctly as an MCP tool and that the extracted CLI remains fully functional independently.

## Components

-   `memory-manager`: Independent CLI package.
-   `opencode-memory-plugin`: Thin MCP wrapper for memory operations.

## Trade-offs

-   **Pros**: Improved modularity, reduced dependency bloat, independent versioning/distribution of CLI and Plugin.
-   **Cons**: Increased complexity in repository management (two repositories to maintain instead of one).

## Tasks

1. Create `memory-manager` repository structure.
2. Migrate CLI code from `opencode-memory-plugin` to `memory-manager`.
3. Update `opencode-memory-plugin/pyproject.toml` to remove CLI dependencies.
4. Replace direct CLI imports/calls in `opencode-memory-plugin` with `uvx` calls.
5. Update `opencode-memory-plugin` tests to account for the structural changes.
6. Verify integration.
