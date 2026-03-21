# Suggested Commands

## Project Setup & Environment
- `uv sync`: Synchronize dependencies
- `uv run opm <cmd>`: Run the CLI tool within the project's environment

## Development Tasks
- `just build`: Build agents
- `just test`: Run the test suite
- `just lint`: Lint with ruff
- `just format`: Format with ruff

## opm CLI Usage
- `opm build --input <dir/file> --output <dir/file>`: Build agent markdown files with explicit permissions
- `opm validate --input <dir/file>`: Validate agent tags
- `opm list-rulesets`: List available tags

## Code Navigation
- `just -f ~/opencode-plugins/justfile -C . ctags`: Generate ctags for the project
