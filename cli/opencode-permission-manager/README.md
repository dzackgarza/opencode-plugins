# opencode-permission-manager

Compiles permission-tagged agent definitions into explicit, inspectable OpenCode agent files.

## Input Format

Standard OpenCode agent YAML+Markdown with an additional `permission_tags` field in the header:

```yaml
---
name: MyAgent
description: Brief description
mode: subagent
permission_tags:
  - orchestrator
  - session_tools
  - bash_unrestricted
---

**SYSTEM_ID: MY_AGENT_MD**

Agent prompt content here...
```

## Output

Expanded agent files with every permission explicitly listed — no inherited defaults, no surprises.

The tool resolves each tag to its corresponding ruleset layer, merges them in order, and outputs a fully-expanded `permission:` block ready for use in `opencode.json`.

## Tag Reference

| Tag                 | Effect                         |
| ------------------- | ------------------------------ |
| `orchestrator`      | Task dispatch, todo management |
| `session_tools`     | Introspection, session read    |
| `bash_unrestricted` | Allow all bash commands        |
| `planner`           | Read all, write plans only     |
| `code_writer`       | Read src+plans, write src      |
| `test_writer`       | Read tests+plans, write tests  |
| `docs_writer`       | Read docs+plans, write docs    |
| `reviewer`          | Read all, write nothing        |
| `researcher`        | Read all, write nothing        |

## Usage

```bash
# Compile a single agent
opm build --input agent.yaml.md --output agents/my-agent.md

# Watch mode
opm watch --input agent.yaml.md --output agents/my-agent.md

# Validate tags only (no output)
opm validate --input agent.yaml.md
```
