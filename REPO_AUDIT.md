# Repo Standards

Prescriptive specification for all repos in this monorepo. Every rule is falsifiable by inspection — no vague adjectives. Violations tracked in `GAPS.md`.

---

# Privacy, Secrets, and Config

## `.envrc` Requirements

Reference: `opencode-plugin-improved-webtools/.envrc`

Compliance — all must be true or the repo is non-conformant:

- Line 1 is exactly `source_up`
- Line 2 is exactly `dotenv_if_exists .env`
- `OPENCODE_CONFIG="$PWD/.config/opencode.json"` and `OPENCODE_CONFIG_DIR="$PWD/.config"` are exported
- `<PLUGIN_NAME_UPPER>_TEST_PASSPHRASE` is exported (plugin-unique non-dictionary phrase)
- Every `process.env.FOO` or `os.environ["FOO"]` reference in `src/` has a corresponding export or comment in `.envrc`
- Optional vars assign their default inline: `export VAR="${VAR:-default}"` — no silent surprises
- No line assigns a live secret value (no `export TOKEN=abc123`) — secrets live in `.env` (gitignored), documented as comments only
- No hardcoded absolute paths anywhere in committed files — use `$HOME`, `$PWD`, `$XDG_CACHE_HOME`

## Constants Consolidation

- Any value appearing in more than one source file (timeout durations, model slugs, port numbers, default URLs) must be defined in `.envrc` or a tracked config file, not duplicated in source
- Version strings are never hardcoded in source — always read from `package.json` or `pyproject.toml` at runtime

---

# Justfile Automation

The canonical automation entrypoint is a lowercase `justfile`. The presence of a capital-J `Justfile` is a build error (enforced by `justfile-hygiene`).

## Required Recipes — All Plugin Types

Every repo must expose all of: `install`, `typecheck`, `test`, `check`, `bump-patch`, `bump-minor`, `release`

Running `just --list` must show all of these.

## Pattern A — TypeScript Plugin

Reference: `opencode-plugin-improved-task/justfile`

```makefile
repo_root := justfile_directory()

justfile-hygiene:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -e "{{repo_root}}/Justfile" ]]; then
      echo "Canonical automation entrypoint is ./justfile; remove ./Justfile." >&2
      exit 1
    fi

install: justfile-hygiene
    direnv exec "{{repo_root}}" bun install

typecheck: justfile-hygiene
    direnv exec "{{repo_root}}" bunx tsc --noEmit

test: justfile-hygiene
    #!/usr/bin/env bash
    set -euo pipefail
    # Clear opencode plugin cache before every test run.
    rm -rf "${XDG_CACHE_HOME:-$HOME/.cache}/opencode"
    exec direnv exec "{{repo_root}}" bun test

test-file file pattern='': justfile-hygiene
    #!/usr/bin/env bash
    set -euo pipefail
    rm -rf "${XDG_CACHE_HOME:-$HOME/.cache}/opencode"
    if [[ -n "{{pattern}}" ]]; then
      exec direnv exec "{{repo_root}}" bun test "{{file}}" --test-name-pattern "{{pattern}}"
    fi
    exec direnv exec "{{repo_root}}" bun test "{{file}}"

check: justfile-hygiene typecheck test

setup-npm-trust:
    npm trust github --repository "dzackgarza/$(basename "{{repo_root}}")" --file publish.yml

publish: check
    npm publish

bump-patch: check
    npm version patch
    git push origin $(git branch --show-current) --tags

bump-minor: check
    npm version minor
    git push origin $(git branch --show-current) --tags

release: bump-patch
```

## Pattern B — Python Package

Reference: `usage-limits/justfile`

```makefile
default:
    @just --list

setup:
    uv venv
    uv sync --all-groups

check: lint typecheck test

fmt:
    uv run ruff format .
    uv run ruff check --fix .

lint:
    uv run ruff check .

typecheck:
    uv run mypy -p <package_name>

test *ARGS:
    uv run pytest {{ARGS}}

v:
    @uv version | awk '{print $2}'

bump-patch: check
    uv version --bump patch
    git add pyproject.toml
    git commit -m "chore: bump version to v$(uv version | awk '{print $2}')"
    git tag v$(uv version | awk '{print $2}')

bump-minor: check
    uv version --bump minor
    git add pyproject.toml
    git commit -m "chore: bump version to v$(uv version | awk '{print $2}')"
    git tag v$(uv version | awk '{print $2}')

release: bump-patch
    git push origin $(git branch --show-current) --tags
    gh release create v$(uv version | awk '{print $2}') --generate-notes

release-minor: bump-minor
    git push origin $(git branch --show-current) --tags
    gh release create v$(uv version | awk '{print $2}') --generate-notes
```

## Pattern C — Hybrid TS + Python Plugin

Reference: `opencode-plugin-improved-webtools/justfile`

```makefile
repo_root := justfile_directory()

# include justfile-hygiene, setup-npm-trust, publish, bump-*, release from Pattern A

install: justfile-hygiene install-ts install-mcp

install-ts: justfile-hygiene
    direnv exec "{{repo_root}}" bun install

install-mcp: justfile-hygiene
    direnv exec "{{repo_root}}" sh -lc 'cd mcp-server && uv sync --dev'

typecheck: justfile-hygiene
    direnv exec "{{repo_root}}" bunx tsc --noEmit

test: justfile-hygiene
    #!/usr/bin/env bash
    set -euo pipefail
    rm -rf "${XDG_CACHE_HOME:-$HOME/.cache}/opencode"
    exec direnv exec "{{repo_root}}" bun test

mcp-test: justfile-hygiene
    direnv exec "{{repo_root}}" sh -lc 'cd mcp-server && uv run python -m pytest'

check: justfile-hygiene typecheck test mcp-test
```

## Git Pre-Commit Hook

The pre-commit hook (`.git/hooks/pre-commit`) must:

- Clear `${XDG_CACHE_HOME:-$HOME/.cache}/opencode` before running
- Run `just check` — not raw `bun test` or `pytest` directly

Compliance:
- `just --list` shows all required recipes?
- `test` recipe clears `${XDG_CACHE_HOME:-$HOME/.cache}/opencode` before running?
- Pre-commit hook runs `just check`, not raw `bun test` or `pytest`?
- Pre-commit hook clears opencode cache before running?
- Lowercase `justfile` only — no `Justfile`?
- All TS recipes run under `direnv exec "{{repo_root}}"` — never bare `bun`/`bunx`?

---

# Dependency Management

- TypeScript: all runtime and dev dependencies declared in `package.json`, installed via `bun install`
- Python: all runtime and dev dependencies declared in `pyproject.toml` under `[project.dependencies]` and `[dependency-groups]`, installed via `uv sync --all-groups`
- MCP servers under `mcp-server/` have their own `pyproject.toml` — not inline pip installs
- No `pip install`, `npm install -g`, or ad-hoc package fetches in any recipe or source file

---

# Local OpenCode Integration

## `.config/` Directory Structure

Checked into the repo. Must contain no absolute paths.

```
.config/
  opencode.json           # Proof agent config — model slug tracked here
  package.json            # Isolated test dependencies
  node_modules/           # gitignored
  plugins/
    <plugin-name>.ts -> ../../src/index.ts   # RELATIVE symlink — never /home/...
```

## `opencode.json` Specification

Every agent entry must contain:
- `"model"`: explicit provider/model slug (e.g., `"github-copilot/gpt-4.1"`) — never omitted or inherited from global config
- `"prompt"`: system prompt that constrains the agent to the proof task (see Zero-Knowledge Proof section)
- `"permission"`: explicit permission block that denies all tools except the one under test

```json
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "<plugin-name>-proof": {
      "description": "Proof agent for <plugin-name> integration tests",
      "mode": "primary",
      "model": "<provider>/<model-slug>",
      "prompt": "You are a matter-of-fact integration-test agent. Follow instructions exactly. When asked to report a verification passphrase or exact text, reply verbatim with no extra text. Do not use any tool not explicitly named in the prompt.",
      "permission": {
        "read": "deny",
        "glob": "deny",
        "grep": "deny",
        "list": "deny",
        "bash": "deny",
        "webfetch": "deny",
        "websearch": "deny",
        "write": "deny",
        "edit": "deny",
        "question": "allow",
        "<tool_under_test>": "allow"
      }
    }
  }
}
```

Rules:
- The model slug is the single tracked record of which model runs proof tests — update it when switching models
- The permission block must deny every tool except the one under test and `question`
- Never use `"Minimal"` or any globally-defined agent as the proof agent
- Plugins loaded via `.config/plugins/<name>.ts` symlinks — relative paths only

## Plugin Directives — Banned Patterns

The following are banned in any `opencode.json`, justfile, or config file:

```
# BANNED — git+ssh requires SSH key, breaks CI, breaks others' clones
git+ssh://github.com/...

# BANNED — absolute file path, machine-specific
file:///home/dzack/...
```

Permitted:
```
# npm slug (auto-updates to latest published)
@dzackgarza/<plugin-name>

# git+https with branch ref (auto-updates on branch push)
git+https://github.com/dzackgarza/<repo>.git#main
```

Commit hashes in git directives are banned in the skeleton config — use `#main` or bare npm slug.

Compliance:
- `OPENCODE_CONFIG` and `OPENCODE_CONFIG_DIR` exported in `.envrc`?
- `.config/opencode.json` defines a repo-local named agent with explicit model slug?
- Every agent entry has a permission block denying all tools except the one under test?
- `.config/plugins/*.ts` are relative symlinks (verify with `ls -la .config/plugins/`)?
- No `git+ssh://`, `file://`, or hardcoded absolute paths in any config?
- Skeleton config uses `#main` or npm slug — no commit hashes?

---

# Tests and Proofs

## Test Directory Structure

TypeScript:
```
tests/
  integration/
    <plugin-name>.test.ts    # Real opencode session harness — zero-knowledge proof
  unit/
    <component>.test.ts      # Pure unit tests for isolated functions
```

Python:
```
tests/
  test_<component>.py        # pytest prefix convention
```

## Isolated Runtime — Required for All TS Integration Tests

Every integration test must create a fully isolated runtime before spawning opencode. This prevents global state, cached plugins, and prior session data from affecting results.

Reference: `opencode-plugin-improved-task/tests/integration/task-plugin.test.ts:97`

```typescript
import { mkdtemp, mkdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

async function createIsolatedRuntime(cwd: string) {
  const root = await mkdtemp(join(tmpdir(), "<plugin-name>-opencode-"));
  const configHome = join(root, "config");
  const cacheHome = join(root, "cache");
  const stateHome = join(root, "state");
  await mkdir(configHome, { recursive: true });
  await mkdir(cacheHome, { recursive: true });
  await mkdir(stateHome, { recursive: true });
  return {
    runtime: {
      cwd,
      env: {
        ...process.env,
        XDG_CONFIG_HOME: configHome,
        XDG_CACHE_HOME: cacheHome,    // isolates ~/.cache/opencode
        XDG_STATE_HOME: stateHome,    // isolates ~/.local/state/opencode
      },
    },
    cleanup: async () => rm(root, { recursive: true, force: true }),
  };
}
```

`XDG_CACHE_HOME` and `XDG_STATE_HOME` must be overridden — not just `XDG_CONFIG_HOME` — so no stale plugin state bleeds in from previous runs.

## Port Allocation — Required for All TS Integration Tests

Tests bind to OS-assigned ephemeral ports. No hardcoded port numbers.

Reference: `opencode-plugin-improved-task/tests/integration/task-plugin.test.ts:74`

```typescript
import { createServer } from "node:net";

async function findFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address() as { port: number };
      server.close((err) => (err ? reject(err) : resolve(port)));
    });
  });
}
```

## Zero-Knowledge Proof — Required for All Integration Tests

A test passes the zero-knowledge criterion if and only if the agent **cannot** pass it without actually calling the tool under test. Three requirements must all hold:

**1. UUID nonce in the prompt**

Generate a nonce at test time. The agent cannot have seen this value in training data.

```typescript
import { randomUUID } from "node:crypto";

const nonce = randomUUID();
const prompt = `Call the ${TOOL_NAME} tool with [required args]. Your response must contain this exact string verbatim: ${nonce}`;
```

**2. Assert the nonce appears in the transcript**

```typescript
const transcript = await runSession(prompt, runtime);
expect(transcript).toContain(nonce);
```

**3. Assert the tool was actually called (not echoed from the prompt)**

The agent's permission block in `.config/opencode.json` must deny all tools except the one under test. This enforces that the only way to succeed is to call the tool — the agent cannot look up the nonce via `read`, `bash`, or any other tool.

If the test involves a value only retrievable via the tool (not present in the prompt), the nonce must be embedded in that value rather than the prompt:

```typescript
// Example: write nonce to a temp file, ask agent to retrieve it via the plugin's read tool
await writeFile(tempFile, nonce);
const prompt = `Use ${TOOL_NAME} to read ${tempFile} and report its contents verbatim.`;
```

## Passphrase Methodology — Sync (One-Shot) Plugin Tests

In addition to the UUID nonce, sync plugin integration tests use a fixed passphrase to verify tool registration and basic invocation. The passphrase is:

- A non-dictionary phrase unique to this plugin (e.g., `SWORDFISH-TASK`)
- Exported from `.envrc` as `<PLUGIN_NAME_UPPER>_TEST_PASSPHRASE`
- **Never** hardcoded in test source — always read from `process.env`
- Used in a prompt that requires the tool to be called, then asserted with exact string match

```typescript
const PASSPHRASE = process.env.<PLUGIN_NAME_UPPER>_TEST_PASSPHRASE;
if (!PASSPHRASE) throw new Error("<PLUGIN_NAME_UPPER>_TEST_PASSPHRASE not set");

const prompt = `Call the ${TOOL_NAME} tool. If it succeeds, include this exact string in your reply: ${PASSPHRASE}`;
// ... run session ...
expect(transcript).toContain(PASSPHRASE);
```

The passphrase test and the UUID nonce test are both required. They serve different purposes: passphrase confirms tool registration; nonce confirms the tool actually ran and returned live data.

## Session Shape: Sync Plugins

Sync plugins complete their work within a single turn. The test:

1. Creates an isolated runtime (temp XDG dirs, ephemeral port)
2. Spawns `opencode serve --port <ephemeral>` pointing at `.config/opencode.json`
3. Sends a single message containing both the passphrase instruction and a UUID nonce
4. Awaits session completion
5. Asserts passphrase and nonce both appear in transcript
6. Asserts the tool-call entry appears in the transcript (not just the text response)
7. Cleans up the isolated runtime

`OPENCODE_BIN` env var must be used for the binary path — never hardcoded:

```typescript
const OPENCODE = process.env.OPENCODE_BIN || "opencode";
```

## Session Shape: Async Plugins

Async plugins (e.g., time-travel, reminder-injection) produce effects outside the session. The test:

1. Creates an isolated runtime
2. Spawns an opencode session that uses the plugin to schedule a future effect
3. Awaits the effect (e.g., callback fires, file written, systemd timer created)
4. Asserts the effect against a UUID nonce embedded at scheduling time
5. Cleans up

Assertion is on the external state change, not on the session transcript alone.

## Rules — All Tests

- No mocks, stubs, or monkey-patching of the plugin or opencode internals
- No hardcoded absolute paths — use `process.env.OPENCODE_BIN`, `process.cwd()`, temp dirs
- No test relies on LLM memory: agent cannot pass by hallucinating, guessing, or reciting from training data (enforced by nonce + permission lock)
- No test re-verifies the internals of tools external to this repo (e.g., do not assert how opencode's own session management works)
- Test agent name is read from the env (exported via `.envrc` → `OPENCODE_CONFIG`) — never hardcoded in test source

Compliance:
- All integration tests create an isolated runtime with `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME`?
- All integration tests use `findFreePort()` — no hardcoded ports?
- All integration tests include a UUID nonce that the agent must return verbatim?
- The nonce cannot be passed by the agent without calling the tool (permission block enforces this)?
- All integration tests assert the tool call appears in the transcript, not just the text?
- All integration tests read `PASSPHRASE` from env — never hardcoded?
- No mocks anywhere in `tests/`?
- No hardcoded absolute paths in test source?

---

# TypeScript Configuration

## Canonical `tsconfig.json`

Reference: `opencode-plugin-improved-task/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ESNext"],
    "types": ["bun-types"],
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "allowImportingTsExtensions": true,
    "noEmit": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*.ts"],
  "exclude": ["node_modules"]
}
```

All six fields (`strict`, `noUnusedLocals`, `noUnusedParameters`, `noImplicitReturns`, `allowImportingTsExtensions`, `noEmit`) must be present and set to `true`. `moduleResolution` must be `"bundler"` (lowercase).

## Canonical `package.json`

```json
{
  "name": "@dzackgarza/<plugin-name>",
  "version": "x.y.z",
  "module": "./src/index.ts",
  "type": "module",
  "exports": {
    ".": "./src/index.ts"
  },
  "files": ["src/"],
  "scripts": {
    "test": "just --justfile justfile test",
    "typecheck": "just --justfile justfile typecheck",
    "check": "just --justfile justfile check"
  },
  "devDependencies": {
    "bun-types": "latest",
    "typescript": "^5.0.0"
  },
  "publishConfig": {
    "access": "public"
  }
}
```

---

# Code Quality

## No Backwards Compatibility

These repos have no external public API consumers. There are no "previous users" to support.

The following are always prohibited — zero tolerance, no exceptions:

- **Legacy interop shims**: renamed `_old` variables, `compat_*` wrappers, version-gated branches of the form `if (legacyMode) { ... }`
- **Dead code**: unreachable branches, commented-out blocks, unused imports, symbols that are never called
- **Unused parameters**: every declared parameter must be used; TypeScript's `noUnusedParameters` enforces this at compile time; Python must pass `ruff` without suppressions
- **Convenience aliases**: do not re-export a symbol under a second name "for ergonomics" — one canonical name, one location
- **Deprecation markers**: no `@deprecated`, no `// TODO: remove`, no `// legacy:` comments — if it shouldn't be there, delete it now
- **Migration scaffolding**: no data-migration helpers, no schema-version guards, no multi-shape input coercions for the sake of old callers

If a refactor breaks an internal caller, fix the caller in the same commit. Do not leave both old and new forms coexisting.

Compliance:
- TypeScript: `noUnusedLocals`, `noUnusedParameters`, `noImplicitReturns` all set to `true` in `tsconfig.json`?
- Python: `ruff check` passes with no `# noqa` suppressions on unused-variable or unused-import rules?
- No commented-out code blocks anywhere in `src/`?
- No `@deprecated`, `// legacy`, or `// TODO: remove` markers anywhere in `src/`?
- No dual-name exports (same symbol exported under two names)?

---

# Release and Publishing

## TypeScript Plugins

```
just bump-patch   →   npm version patch + git tag + push
just publish      →   npm publish (requires 2FA or GitHub trusted publisher)
just release      →   bump-patch + publish
```

GitHub Action triggers on npm release event and re-publishes. `just setup-npm-trust` configures the trusted publisher (one-time, per repo).

## Python Packages

```
just release       →   bump-patch + push tags + gh release create --generate-notes
just release-minor →   bump-minor + push tags + gh release create --generate-notes
```

GitHub Action triggers on `v*` tag push.

---

# Tool and MCP Descriptions

Every tool description must:

- Begin with `Use when` — no exceptions
- Be written for the agent calling the tool (first person: "Use when you want to..." not "Use when the agent wants to...")
- Include the version string, read dynamically from `package.json` or `pyproject.toml`
- List the most common happy-path invocations with concrete parameter examples
- Fit in under 150 tokens — no exposition, no marketing

**Non-compliant:** `webfetch: Fetches a URL for you. Returns the page content.`
**Compliant:** `webfetch (v0.1.1): Use when you need to retrieve the content of a URL. Supports HTML pages, PDFs, and arxiv links. Pass url as a string.`

Compliance:
- Every tool description starts with `Use when`?
- Agent-facing framing throughout (not user-facing)?
- Version dynamically populated?
- Concrete parameter examples present?
- Under 150 tokens?

---

# User and Agent Feedback

## Tool Result Shape

Every tool must return a result that contains:

```typescript
type ToolResult = {
  success: boolean;
  version: string;        // read from package.json at runtime — never hardcoded
  result: string | object; // the actual output
  error?: string;         // present when success is false
  issueUrl: string;       // always: "https://github.com/dzackgarza/<repo>/issues"
};
```

When `success` is `false`, `error` must be a human- and agent-readable message that:
- States what failed
- Includes `issueUrl` (the full GitHub issues URL for this repo)

Every tool call must also inject a chat-visible message (not just a tool result) summarizing the outcome. This is done via the opencode-manager chat injection API, not by returning a long string.

Compliance:
- Every tool result includes `success`, `version`, `result`, `issueUrl`?
- Error results include a message instructing the agent to file an issue at `issueUrl`?
- Every tool call injects a chat-visible message?
- `version` is read from `package.json` at runtime — not hardcoded?

---

# README Standards

The README must be self-contained and make sense to a reader who has never seen this repo before and has no context about the monorepo, opencode, or adjacent packages. Every item below is a concrete, falsifiable requirement.

## Purpose and Value

- States the specific problem this repo solves in the first paragraph — no vague mission statements
- Describes the specific value-add, unique perspective, or feature set that distinguishes this from alternatives
- Does not "sell" the repo — no superlatives, no LLM-isms, no marketing copy

## Agent Transparency

For plugin and MCP repos, the README must document what the agent actually sees:

- The name and description of every tool exposed, as it appears in the tool schema
- The input schema for each tool (parameter names, types, what they do)
- Representative example of what a successful tool result looks like
- Any side effects the tool produces (files written, services called, global state modified)

This section does not need to reproduce every detail of the source — it must give an agent or developer reading the README enough information to know what the tool does, how to invoke it, and what to expect back.

## Features

- Explicit list of every feature that is actually available and working
- No implied or aspirational features — only what is currently functional
- If behavior differs across modes, configs, or env var settings, each variant is listed

## Dependencies and Isolation

- The repo is standalone: all dependencies declared in `package.json` or `pyproject.toml` and installable via `bun install` / `uv sync` — no dependency on local paths or sibling repos
- All external services the repo depends on are named (e.g., PostgreSQL, SearxNG, Zotero local API) with a link to their setup documentation — not inline setup instructions for third-party tools
- Any external tools that must be installed and running before use are listed with version requirements

## Environment Variables

- Every env var the repo reads is listed, with:
  - The exact variable name
  - Whether it is required or optional
  - The default value if optional
  - What it controls
- This list is the canonical reference; `.envrc` is the machine-readable equivalent — the README does not duplicate `.envrc` comments verbatim, it summarizes them

## External Modifications

- Any writes to locations outside the repo directory are explicitly documented: global config dirs (`~/.config/opencode/`, `~/.local/share/`, systemd unit files, cron entries, etc.)
- The scope and reversibility of each modification is stated

## Setup Instructions

- Step-by-step instructions to go from a fresh clone to a working installation
- Installation uses `npx`/`uvx` quick-start or opencode `git+https` directive — not `git clone` — where possible
- For required external tools (e.g., PostgreSQL, SearxNG), links to their official setup docs are provided rather than inline instructions
- Config examples for at least: opencode, claude, codex (these are nearly identical; one block with comments suffices)
- `just --help` and `--help` flags on scripts are referenced as the canonical source of CLI/recipe documentation — the README does not duplicate them

## What the README Does Not Contain

- Changelogs, todos, past project state, migration notes
- Dump of justfile recipes (belongs in `just --list`)
- Dump of CLI flags (belongs in `--help`)
- Inline setup instructions for third-party tools — link out instead

## Compliance

- Reader with no prior context can understand what the repo does from the first paragraph?
- Purpose and specific value-add stated?
- Every tool/MCP exposed is named with its description, input schema, and example output?
- Every feature listed is currently functional?
- All external service dependencies named with links to their setup docs?
- Every env var listed with name, required/optional, default, and purpose?
- All writes outside the repo directory documented?
- Setup instructions complete and use `npx`/`uvx` or `git+https` — not `git clone`?
- README points to `just --list` and `--help` rather than duplicating that content?
- Ko-Fi button present?
- No selling language, no LLM-isms, no superlatives?
