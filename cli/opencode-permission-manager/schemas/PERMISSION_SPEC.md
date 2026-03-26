# OpenCode Permission Field Specification

## Source

Extracted from upstream OpenCode source code via Deepwiki analysis of:

- `packages/opencode/src/config/config.ts` — Permission Zod schema
- `packages/opencode/src/permission/next.ts` — Permission evaluation logic
- Documentation in `packages/web/src/content/docs/`

## Permission Object Structure

The `permission` field in agent markdown frontmatter is an object where:

- **Keys** = tool names (e.g., `bash`, `edit`, `read`)
- **Values** = either a simple string or a glob-based rule object

### Simple Form (no path restrictions)

```yaml
permission:
  bash: allow
  edit: deny
  webfetch: ask
```

Values: `"allow"`, `"ask"`, or `"deny"`

### Glob-Based Form (path/command restrictions)

```yaml
permission:
  bash:
    '*': ask # default for all commands
    'git *': allow # specific allow
    'rm *': deny # specific deny
  edit:
    '*': deny
    'src/*': allow
    '*.md': ask
```

**Key rules for globs:**

- `*` matches zero or more characters (including `/`)
- `?` matches exactly one character
- Last matching rule wins
- `~` or `$HOME` expands to home directory

## Valid Tool Names

### Core Tools

| Tool    | Description                                               |
| ------- | --------------------------------------------------------- |
| `read`  | Reading files                                             |
| `edit`  | File modifications (covers edit, write, patch, multiedit) |
| `glob`  | File globbing                                             |
| `grep`  | Content searching with regex                              |
| `list`  | Listing directory contents                                |
| `bash`  | Running shell commands                                    |
| `task`  | Launching subagents                                       |
| `skill` | Loading skills by name                                    |
| `lsp`   | LSP queries                                               |

### Web Tools

| Tool         | Description          |
| ------------ | -------------------- |
| `webfetch`   | Fetching URL content |
| `websearch`  | Web searching        |
| `codesearch` | Code searching       |

### Todo Tools

| Tool        | Description        |
| ----------- | ------------------ |
| `todoread`  | Reading todo list  |
| `todowrite` | Updating todo list |

### Special Permissions

| Tool                 | Description                             |
| -------------------- | --------------------------------------- |
| `external_directory` | Paths outside project working directory |
| `question`           | Question tool                           |
| `doom_loop`          | Repeated identical tool calls (3x)      |

## Default Behavior

**If tool is NOT listed**: defaults to `"allow"` (permissive)

**Exceptions with stricter defaults:**

- `external_directory`: defaults to `"ask"`
- `doom_loop`: defaults to `"ask"`
- `read` for `.env` files: denied by default
  - `*.env`: deny
  - `*.env.*`: deny
  - `*.env.example`: allow

## Path Matching for Edit Tools

Edit permissions work on **file paths**, not commands:

```yaml
permission:
  edit:
    '*': deny # deny all by default
    'src/*': allow # allow src directory
    '*.md': ask # markdown files ask
```

## Path Matching for Bash

Bash permissions work on **command strings**:

```yaml
permission:
  bash:
    '*': ask # ask by default
    'git *': allow # allow git commands
    'npm *': allow # allow npm commands
    'rm *': deny # deny removal
```

## External Directory

Triggered when any tool accesses paths outside the working directory:

```yaml
permission:
  external_directory:
    '~/.dotfiles/*': allow
    '~/projects/*': allow
    '*': deny
```

Note: Even with `external_directory: allow`, you still need the tool-specific permission (e.g., `read: allow`).

## MCP Tools

MCP tools are controlled by their tool names directly:

```yaml
permission:
  'mcp_server_tool_name': allow
```

## Common Gotchas

1. **Unlisted tools = allow**: If you forget to list a tool, it runs without approval
2. **Last rule wins**: Order matters in glob rules — specific rules must come after general
3. **external_directory**: Even if `read: allow`, external paths need this too
4. **Agent precedence**: Agent permissions override global permissions
5. **.env files**: Read access to `.env` is denied by default

## Complete YAML Example

```yaml
---
description: Code reviewer agent
mode: subagent
permission:
  read: allow
  edit: deny
  glob: allow
  grep: allow
  list: allow
  bash:
    '*': ask
    'git *': allow
    'grep *': allow
    'rg *': allow
  task: deny
  skill: allow
  lsp: allow
  webfetch: deny
  websearch: allow
  codesearch: allow
  todowrite: allow
  todoread: allow
  question: allow
  external_directory:
    '*': ask
  doom_loop: ask
---
<prompt content>
```

## JSON Schema Reference

The output must validate against the upstream Zod schema in `packages/opencode/src/config/config.ts` → `Permission` type.
