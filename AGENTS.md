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
- **NEVER** add or override `"model"` in a per-plugin repo-root `opencode.json` when the repo uses the standard global `plugin-proof` agent. That model is set once in `~/.config/opencode/opencode.json`.
- Anthropic models bill per token. Using them for tests wastes money and violates this policy.
- If `github-copilot/gpt-4.1` is unavailable, investigate auth — do not switch providers.

## Quick Reference

- **Central CI workflows**: use [.github/workflows/python-cli-ci.yml](/home/dzack/opencode-plugins/.github/workflows/python-cli-ci.yml), [.github/workflows/python-cli-publish.yml](/home/dzack/opencode-plugins/.github/workflows/python-cli-publish.yml), [.github/workflows/bun-plugin-ci.yml](/home/dzack/opencode-plugins/.github/workflows/bun-plugin-ci.yml), and [.github/workflows/bun-plugin-publish.yml](/home/dzack/opencode-plugins/.github/workflows/bun-plugin-publish.yml) as the only workflow templates.
- **OpenCode config**: CI and local proof runs rely on standard precedence: global `~/.config/opencode/opencode.json` plus repo-root `opencode.json`. Do not wire `OPENCODE_CONFIG` or `OPENCODE_CONFIG_DIR` unless a repo documents a real exception.
- **Audit checklist**: See `REPO_AUDIT.md` (symlink to skill) before pushing.
- **Structure**: Each subdirectory is an independent package repo.

## Navigation

- `GUIDE.md` in skill → Development workflow and conventions
- `AUDIT.md` in skill → Post-hoc compliance rubric
- `README.md` → Plugin listings and high-level orientation
- `opencode-cli/SKILL.md` → CLI and manager commands
- `opencode-cli/PLUGINS.md` → Hook and event SDK reference
