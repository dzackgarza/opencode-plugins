# opm (opencode-permission-manager)

## Purpose
A tool to compile high-level permission tags into explicit OpenCode-compatible permission sets for agents. It resolves tags to predefined rulesets and computes a minimal permission set for individual agents, taking into account global defaults.

## Tech Stack
- Python (uv)
- Typer (CLI)
- PyYAML (YAML parsing/dumping)
- pytest (Testing)

## Project Structure
- `src/opm/`: Core logic
    - `cli.py`: CLI entry points
    - `compiler.py`: Permission tag resolution and merging
    - `parser.py`: YAML frontmatter parsing from Markdown
    - `transform.py`: End-to-end transformation of agent files
- `tests/`: Test suite

## Development Commands
- `just build`: Build agents (defined in justfile)
- `just test`: Run tests
- `just lint`: Lint with ruff
- `just format`: Format with ruff

## Usage
- `opm build --input <dir/file> --output <dir/file>`: Generate agents with permissions
- `opm list-rulesets`: Show available tags
- `opm validate --input <dir/file>`: Check if agent tags are valid

## Key Patterns
- Rulesets are defined as lists of permission "layers".
- Layers are deep-merged (later wins).
- Permission blocks are injected into agent Markdown frontmatter.
