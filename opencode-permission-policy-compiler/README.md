# opencode-permission-policy-compiler

Compile OpenCode markdown agents that use a custom `policies:` frontmatter list into standard OpenCode markdown with an explicit `permission:` block.

## Usage

```bash
cat agent.md | uv run opencode-permission-policy-compiler > compiled-agent.md
```

## Behavior

- Reads one markdown agent from `stdin`
- Loads the global OpenCode baseline from `~/.config/opencode/opencode.json`
- Resolves known policy names from fixed in-code mappings
- Resolves policies in listed order, with later policies overriding earlier policies
- Uses the top-level OpenCode `permission` block as the global baseline
- Emits only the minimal agent-local `permission:` overlay needed to reproduce the requested outcome
- Removes the custom `policies:` field from output

## Input

```yaml
---
description: Code review without edits
mode: subagent
policies:
  - review
  - git-inspect
---
Only analyze code and report issues.
```

## Output

```yaml
---
description: Code review without edits
mode: subagent
permission:
  edit: deny
  webfetch: deny
  websearch: deny
  bash:
    "*": ask
    "git diff *": allow
    "git log *": allow
    "git status *": allow
---
Only analyze code and report issues.
```
