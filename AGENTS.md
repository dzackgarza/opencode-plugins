# OpenCode Plugins Development

This is the shared development workspace for OpenCode plugin packages.

## Required Skills

When working in this repository, reference these skills:

| Skill                           | Purpose                                                                                                                                   |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **opencode-plugin-development** | Primary skill for development workflow, proof design, testing rules, and audit criteria. See `GUIDE.md` and `AUDIT.md` within this skill. |
| **opencode-cli**                | OpenCode CLI commands, config model, and manager (`opx`) workflow syntax.                                                                 |
| **justfile**                    | Just command runner patterns and recipes.                                                                                                 |
| **git-guidelines**              | Git workflow and safety practices.                                                                                                        |

## MODEL CHOICE POLICY — MANDATORY, NEVER OVERRIDE

ALL integration tests use `github-copilot/gpt-4.1`. This is a **free model** requiring no per-request payment.

- **NEVER** change the test model to any Anthropic model (`claude-*`), any OpenAI paid model, or any other paid provider.
- **NEVER** add or override `"model"` in a per-plugin `tests/integration/opencode.json`. The model is set once in the global `plugin-proof` agent definition in `~/.config/opencode/opencode.json`.
- Anthropic models bill per token. Using them for tests wastes money and violates this policy.
- If `github-copilot/gpt-4.1` is unavailable, investigate auth — do not switch providers.

## Quick Reference

- **Test sandbox**: `just test-sandbox-up` / `just test-sandbox-down`. Creates an isolated opencode server on `http://127.0.0.1:4097` with its own tmp HOME/XDG dirs plus a sandbox-local project dir, and writes `.test-sandbox-env.sh` for package repos to source.
- **Audit checklist**: See `REPO_AUDIT.md` (symlink to skill) before pushing.
- **Structure**: Each subdirectory is an independent package repo.

## Navigation

- `GUIDE.md` in skill → Development workflow and conventions
- `AUDIT.md` in skill → Post-hoc compliance rubric
- `README.md` → Plugin listings and high-level orientation
- `opencode-cli/SKILL.md` → CLI and manager commands
- `opencode-cli/PLUGINS.md` → Hook and event SDK reference
