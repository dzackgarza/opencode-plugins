# opencode-permission-policy-compiler

Compile OpenCode markdown agents that use a custom `policies:` frontmatter list into standard OpenCode markdown with an explicit `permission:` block.

## Usage

```bash
cat agent.md | uv run opencode-permission-policy-compiler > compiled-agent.md
uv run opencode-permission-policy-compiler install-config
uv run opencode-permission-policy-compiler set-global-policy global
uv run opencode-permission-policy-compiler doctor
```

## Behavior

- Reads one markdown agent from `stdin`
- Loads the global OpenCode baseline from `~/.config/opencode/opencode.json`
- Resolves known policy names from `$XDG_CONFIG_HOME/opencode-permission-policy-compiler/config.toml`
- Falls back to `~/.config/opencode-permission-policy-compiler/config.toml` when `XDG_CONFIG_HOME` is unset
- Uses the CLI TOML `[mcps]` section to declare which OpenCode MCP servers should be included in permission inventory checks
- Treats a policy as this CLI's collection of OpenCode permissions
- Allows markdown agents to omit `policies:` entirely, in which case they inherit the global OpenCode permissions unchanged
- Accepts existing agent-local `permission:` frontmatter and merges policy-derived permissions into it before emitting the final minimal overlay
- Resolves policies in listed order, with later policies overriding earlier policies
- Automatically applies the `subagents` policy to markdown agents with `mode: subagent`, even if that policy is not listed explicitly
- Rejects markdown agents that declare deprecated `tools:` frontmatter
- Uses the top-level OpenCode `permission` block as the global permission baseline
- Emits only the minimal agent-local `permission:` overlay needed to reproduce the requested policy outcome
- Removes the custom `policies:` field from output
- `install-config` writes a new XDG policy TOML for this CLI by discovering the live OpenCode tool inventory and configured MCP tools
- `set-global-policy <policy>` rewrites the live `~/.config/opencode/opencode.json` top-level `permission` block with the permissions defined by the named CLI policy while preserving unrelated top-level config keys
- `doctor` validates the XDG policy TOML, compares this CLI's `policies.global` against the live OpenCode `permission` block, probes the configured/default OpenCode server health/tool-ID endpoints, and reports how the global CLI policy differs from live OpenCode permissions

The canonical repo copy of the policy config is [config.toml](/home/dzack/opencode-plugins/opencode-permission-policy-compiler/config.toml).

## Global Policy Writes

```bash
uv run opencode-permission-policy-compiler set-global-policy subagents
```

This command:

- reads the existing global OpenCode config from `~/.config/opencode/opencode.json`
- resolves the named policy from the XDG-installed policy config
- overwrites the top-level `permission` object with the permissions defined by that policy
- preserves unrelated top-level config keys such as `model`, `formatter`, or `provider`

## Config Installation

```bash
uv run opencode-permission-policy-compiler install-config
```

This command:

- discovers the live OpenCode tool inventory from the running server
- discovers configured MCP tools via `mcp2cli`
- writes `$XDG_CONFIG_HOME/opencode-permission-policy-compiler/config.toml`
- fails if that file already exists
- emits a baseline `policies.global` with `"allow"` for every known tool and explicit defaults for `external_directory` and `doom_loop`
- includes commented examples for path- and command-specific overrides

## Doctor

```bash
uv run opencode-permission-policy-compiler doctor
```

This command:

- validates `$XDG_CONFIG_HOME/opencode-permission-policy-compiler/config.toml`
- reads this CLI's `policies.global` as the global policy under diagnosis
- reports whether the live OpenCode top-level `permission` block currently reflects that global policy
- explains the global policy vs OpenCode permission contract and prints the concrete diff when the live OpenCode permission block diverges from `policies.global`
- probes `/global/health` and `/experimental/tool/ids` on the configured/default OpenCode server URLs
- resolves the configured MCP server names from this CLI's `[mcps]` config against the live OpenCode `mcp` config and queries their tools via `mcp2cli`
- labels the tool and non-tool checklists as `In Global Policy?` so the `[x]` / `[ ]` marks are explicit
- marks which OpenCode tools have explicit permissions in this CLI's `policies.global`
- reports whether this CLI's `policies.global` explicitly sets the non-tool OpenCode permissions `external_directory` and `doom_loop`
- explains when permissions defined by this CLI's `policies.global` are not found in the current live toolset, which may indicate stale policy entries or incomplete local tool discovery

## Input

```yaml
---
description: Math prover subagent
mode: subagent
---
Prove the conjecture computationally.
```

## Output

```yaml
---
description: Math prover subagent
mode: subagent
permission:
  task: deny
  question: deny
  submit_plan: deny
  plannotator_review: deny
  plannotator_annotate: deny
---
Prove the conjecture computationally.
```
