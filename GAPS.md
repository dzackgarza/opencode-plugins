# Repo Audit Violations

Generated from audit against `REPO_AUDIT.md`. All violations require remediation.

---

## CRITICAL

### Secret token committed in tracked file

`usage-limits/.envrc`: `OPENROUTER_SINK_TOKEN=ameUcTYfefC1Gp-sKHQI4NEyh4xQPugHKMO3nJu2PuM` — live token assigned, not commented

**Fix:** Remove value, document as `.env` entry only: `# OPENROUTER_SINK_TOKEN=<token>`

---

### Banned `git+ssh://` directives in source

| File | Location |
|---|---|
| `opencode-plugin-improved-task/src/index.ts` | line 16 — `MANAGER_PACKAGE` constant |
| `opencode-postgres-memory-plugin/tests/integration/postgres-memory-plugin.test.ts` | line 16 — `MANAGER_PACKAGE` constant |
| `opencode-manager/README.md` | installation example uses `npx --yes --package=git+ssh://...` |

**Fix:** Replace with `git+https://github.com/dzackgarza/opencode-manager.git` or npm slug.

---

### Banned `file://` directives in skeleton config

`~/ai/opencode/configs/config_skeleton.json`:
- `"file:///home/dzack/ai/opencode/tools/canonical-plugin-probes/canonical-smoke-fileproof.ts"`
- `"file:///home/dzack/ai/opencode/tools/canonical-plugin-probes/canonical-shadowing-fileproof.ts"`

**Fix:** Remove or replace with `git+https://` references.

---

### Commit-pinned plugin entries in skeleton config

`~/ai/opencode/configs/config_skeleton.json` — all 8 plugins pinned to commit hashes:

- `opencode-plugin-improved-task#e4355344fbe5f0590ed13424918d730d04a56aec`
- `opencode-plugin-improved-todowrite#061566f8bb2ea6f663e50ef4ccd11e9c2be4d7f7`
- `opencode-plugin-improved-webtools#7c5159ae0f08d8c10969c4afc3d47e982ebc11e6`
- `opencode-plugin-prompt-transformer#ad9b30c9a3eca8556ba8ddcc7d0feb6c361235d4`
- `opencode-plugin-reminder-injection#c9a8c76c7444f33baaaead17a2d8bfa73a058cf7`
- `opencode-postgres-memory-plugin#4a14d102699667bd874b8550b14c8cdeef0259d9`
- `opencode-time-travel-plugin#fbd33f84d611afb98bc8fb49409aeb8d531b24ea`
- `opencode-zotero-plugin#e0c69b080e2251ab9dc3c2fabf3769ce6664ce25`

**Fix:** Replace all with `#main` or bare npm slug.

---

### Leaked absolute paths in committed files

| Repo | File | Path leaked |
|---|---|---|
| `opencode-manager` | `README.md` | `/home/dzack/.opencode/bin/opencode` |
| `opencode-plugin-improved-task` | `.config/opencode.json` | `/home/dzack/opencode-plugins/...` |
| `opencode-plugin-improved-task` | `tests/integration/task-plugin.test.ts:7` | `/home/dzack/.opencode/bin/opencode` |
| `opencode-plugin-improved-task` | `DEBUGGING.md` | `/home/dzack/.opencode/bin/opencode` |
| `opencode-plugin-prompt-transformer` | `tests/integration/prompt-router.test.ts` | `/home/dzack/.opencode/bin/opencode` |
| `opencode-plugin-prompt-transformer` | `README.md` | references `./ai/prompts/` and `./ai/opencode/.venv` as runtime deps |
| `opencode-postgres-memory-plugin` | `tests/integration/postgres-memory-plugin.test.ts:11` | `/home/dzack/.opencode/bin/opencode` hardcoded fallback |
| `opencode-time-travel-plugin` | `.config/opencode.json` | `/home/dzack/opencode-plugins/...` |
| `opencode-time-travel-plugin` | `tests/integration/systemd-backed-reminders.test.ts` | `HOME_DIR = "/home/dzack"` |
| `opencode-zotero-plugin` | `.venv/lib/.../direct_url.json` | `/home/dzack/opencode-plugins/...` |
| `usage-limits` | `.venv/lib/.../direct_url.json` | `/home/dzack/opencode-plugins/...` |
| `usage-limits` | `qwen_debug.json` (93MB) | extensive `/home/dzack/` paths — delete this file |

**Fix:** Replace with env vars (`$OPENCODE_BIN`, `$PWD`, etc.) or remove debug files.

---

## HIGH

### Tests: no zero-knowledge proof (UUID nonce) in any integration test

None of the integration tests generate a per-run nonce. All rely on passphrase alone, which does not prove the tool executed live (a cached or hallucinated response containing the passphrase would pass).

| Repo | Test file |
|---|---|
| `opencode-plugin-improved-task` | `tests/integration/task-plugin.test.ts` |
| `opencode-plugin-improved-todowrite` | `tests/integration/todowrite-plugin.test.ts` |
| `opencode-plugin-improved-webtools` | `tests/integration/webtools-plugin.test.ts` |
| `opencode-plugin-prompt-transformer` | `tests/integration/prompt-router.test.ts` |
| `opencode-postgres-memory-plugin` | `tests/integration/postgres-memory-plugin.test.ts` |
| `opencode-time-travel-plugin` | `tests/integration/time-travel-plugin.test.ts` |

**Fix:** Add `import { randomUUID } from "node:crypto"`. Generate `nonce = randomUUID()` per test, inject into prompt, assert `expect(transcript).toContain(nonce)`.

---

### Tests: missing XDG runtime isolation

Tests must override `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `XDG_STATE_HOME` to temp dirs. Stale opencode plugin state from prior runs bleeds in otherwise.

| Repo | Test file | Missing |
|---|---|---|
| `opencode-plugin-improved-webtools` | `tests/integration/webtools-plugin.test.ts` | All three XDG dirs — no isolation at all |
| `opencode-plugin-prompt-transformer` | `tests/integration/prompt-router.test.ts` | All three XDG dirs — no isolation at all |
| `opencode-postgres-memory-plugin` | `tests/integration/postgres-memory-plugin.test.ts` | All three XDG dirs — no isolation at all |
| `opencode-time-travel-plugin` | `tests/integration/time-travel-plugin.test.ts` | `XDG_CACHE_HOME`, `XDG_STATE_HOME` |
| `opencode-time-travel-plugin` | `tests/integration/systemd-backed-reminders.test.ts` | All three XDG dirs |
| `opencode-time-travel-plugin` | `tests/integration/callback-firing.test.ts` | All three XDG dirs |

**Fix:** Extend `createIsolatedRuntime` to create and set all three dirs:
```typescript
XDG_CONFIG_HOME: configHome,
XDG_CACHE_HOME:  cacheHome,
XDG_STATE_HOME:  stateHome,
```

---

### Tests: hardcoded port bases instead of `findFreePort()`

| File | Line | Value |
|---|---|---|
| `opencode-time-travel-plugin/tests/integration/systemd-backed-reminders.test.ts` | ~116 | `42980 + Math.floor(Math.random() * 1000)` |
| `opencode-time-travel-plugin/tests/integration/callback-firing.test.ts` | ~72 | `41980 + Math.floor(Math.random() * 1000)` |

**Fix:** Replace with `findFreePort()` from `node:net` (see `task-plugin.test.ts:74` for reference).

---

### Tests: hardcoded passphrase fallback in source

`opencode-plugin-improved-todowrite/tests/integration/todowrite-plugin.test.ts` line ~17: `"SWORDFISH-TODO-TREE"` assigned as fallback when env var is absent.

**Fix:** Remove fallback. Throw if `IMPROVED_TODOWRITE_TEST_PASSPHRASE` is not set: `if (!PASSPHRASE) throw new Error(...)`.

---

### Tests: missing integration tests entirely

| Repo | Status |
|---|---|
| `opencode-zotero-plugin` | Has Python tests in `python/tests/` but no TS integration tests for the plugin wrapper itself |

---

### `.envrc`: missing `source_up`

- `opencode-plugin-prompt-transformer/.envrc`
- `opencode-plugin-reminder-injection/.envrc`

**Fix:** Add `source_up` as line 1.

---

### `.envrc`: `dotenv_if_exists .env` not on line 2

- `opencode-postgres-memory-plugin/.envrc`: line 2 is blank

**Fix:** Remove blank line; `dotenv_if_exists .env` must be line 2.

---

### `.envrc`: missing or misnamed test passphrase exports

| Repo | Current | Required |
|---|---|---|
| `opencode-plugin-improved-todowrite` | `IMPROVED_TODO_VERIFICATION_PASSPHRASE` | `IMPROVED_TODOWRITE_TEST_PASSPHRASE` |
| `opencode-time-travel-plugin` | `TIME_TRAVEL_TEST_SEED` | `TIME_TRAVEL_PLUGIN_TEST_PASSPHRASE` |
| `opencode-plugin-improved-webtools` | *(missing)* | `IMPROVED_WEBTOOLS_TEST_PASSPHRASE` |
| `opencode-plugin-mcp-shim` | *(missing)* | `MCP_SHIM_TEST_PASSPHRASE` |
| `opencode-plugin-prompt-transformer` | *(missing)* | `PROMPT_TRANSFORMER_TEST_PASSPHRASE` |
| `opencode-plugin-reminder-injection` | *(missing)* | `REMINDER_INJECTION_TEST_PASSPHRASE` |

Also: test source for `improved-todowrite` must be updated to read the renamed var.

---

### Justfile: missing `bump-patch`, `bump-minor`, `release` recipes

All repos except `usage-limits` and `opencode-time-travel-plugin`:

`opencode-plugin-improved-task`, `opencode-plugin-improved-todowrite`, `opencode-plugin-improved-webtools`, `opencode-plugin-mcp-shim`, `opencode-plugin-prompt-transformer`, `opencode-plugin-reminder-injection`, `opencode-postgres-memory-plugin`, `opencode-zotero-plugin`, `opencode-manager`, `ai-prompts`, `llm-runner`, `llm-templating-engine`, `opencode-transcripts`

---

### Justfile: `test` recipe does not clear opencode cache

All repos. The `test` recipe must run `rm -rf "${XDG_CACHE_HOME:-$HOME/.cache}/opencode"` before invoking the test runner.

---

### Pre-commit hook absent or non-conformant

| Repo | Status |
|---|---|
| `opencode-time-travel-plugin` | Hook exists but runs raw `bun test` — must run `just check`; must clear opencode cache |
| All other repos | No pre-commit hook at all |

---

### `tsconfig.json`: missing strict flags

| Repo | Missing fields |
|---|---|
| `opencode-plugin-mcp-shim` | `noUnusedLocals`, `noUnusedParameters`, `noImplicitReturns` |
| `opencode-plugin-reminder-injection` | `noUnusedLocals`, `noUnusedParameters`, `noImplicitReturns` |
| `opencode-postgres-memory-plugin` | `noUnusedLocals`, `noUnusedParameters`, `noImplicitReturns`; `moduleResolution` is `"Bundler"` (must be lowercase) |
| `opencode-time-travel-plugin` | `noUnusedLocals`, `noUnusedParameters`, `noImplicitReturns`; `moduleResolution` is `"Bundler"` (must be lowercase) |

---

### `package.json`: missing required fields

**Missing `"type": "module"`:**
`improved-task`, `improved-todowrite`, `improved-webtools`, `prompt-transformer`, `reminder-injection`, `time-travel-plugin`, `zotero-plugin`

**Missing `"exports"` field:**
`improved-task`, `improved-todowrite`, `improved-webtools`, `mcp-shim`, `prompt-transformer`, `reminder-injection`, `postgres-memory-plugin`, `time-travel-plugin`, `zotero-plugin`

**Missing `"files": ["src/"]`:**
`improved-task`, `improved-todowrite`, `improved-webtools`, `prompt-transformer`, `reminder-injection`, `time-travel-plugin`, `zotero-plugin`

**`"scripts"` delegate to raw `bun`/`tsc` instead of `just --justfile justfile <recipe>`:**

| Repo | Scripts needing fix |
|---|---|
| `opencode-plugin-improved-webtools` | `test`, `typecheck`; missing `check` |
| `opencode-plugin-prompt-transformer` | `test`, `typecheck`; missing `check` |
| `opencode-plugin-reminder-injection` | `test`, `typecheck`; missing `check` |
| `opencode-time-travel-plugin` | `test`, `typecheck` |
| `opencode-zotero-plugin` | missing `test` entirely |

---

## MEDIUM

### README: missing Ko-Fi button

- `opencode-zotero-plugin`
- `ai-prompts`

---

### README: missing tool/MCP schema documentation

The following plugin repos do not document the name, input schema, or example output for every tool they expose:

`improved-task`, `improved-todowrite`, `mcp-shim`, `prompt-transformer`, `reminder-injection`, `postgres-memory-plugin`, `zotero-plugin`, `opencode-manager`

`improved-webtools` and `time-travel-plugin` have partial tool documentation but are missing example outputs.

---

### README: missing or incomplete env var table

All repos must list every env var with: exact name, required/optional, default value, what it controls.

| Repo | Status |
|---|---|
| `improved-task` | No env vars section |
| `improved-todowrite` | No env vars section |
| `mcp-shim` | No env vars section |
| `prompt-transformer` | No env vars section |
| `reminder-injection` | Incomplete — missing required/optional/default |
| `postgres-memory-plugin` | Partial |
| `zotero-plugin` | Inline only, not formal table |
| `opencode-manager` | Missing most |
| `ai-prompts` | Missing `PROMPTS_DIR` default/required |
| `llm-runner` | Shows snippet but not formal |
| `llm-templating-engine` | Shows snippet but not formal |
| `opencode-transcripts` | Absent |

---

### README: missing external service dependency links

| Repo | Missing |
|---|---|
| `opencode-postgres-memory-plugin` | PostgreSQL setup link, pgvector setup link |
| `opencode-zotero-plugin` | docling setup link, mineru setup link |
| `opencode-plugin-prompt-transformer` | Links for ai/opencode external runtime deps |
| `usage-limits` | Provider API documentation links |

---

### README: missing side effects documentation

All plugin repos that write outside the repo directory must document it. Currently undocumented:

| Repo | Undocumented side effects |
|---|---|
| `opencode-time-travel-plugin` | systemd unit files, cron entries, callback state dir |
| `opencode-postgres-memory-plugin` | PostgreSQL database writes, schema changes |
| `opencode-zotero-plugin` | PDF attachment back to Zotero item |
| `opencode-plugin-improved-task` | Transcript files written to session dir |

---

### README: past state or changelog content present

- `opencode-plugin-improved-webtools/README.md`: "NOTE: Currently missing `wikipedia_html_to_markdown.py` script in some environments" — documents a gap, not current stable state
- `opencode-time-travel-plugin/README.md`: full "Release Process" section (belongs in CONTRIBUTING or nowhere)

---

### README: missing or weak purpose statement

The following repos open without a clear statement of the specific problem solved and unique value-add:

`improved-todowrite`, `mcp-shim`, `reminder-injection`, `opencode-manager`, `ai-prompts`, `llm-runner`, `llm-templating-engine`, `opencode-transcripts`

---

### README: missing explicit features list

All repos except `improved-webtools` and `time-travel-plugin`.

---

### Justfile: recipe naming inconsistencies

| Repo | Issue |
|---|---|
| `opencode-postgres-memory-plugin` | `setup` instead of `install` |
| `usage-limits` | `setup` instead of `install` |
| `ai-prompts` | no `install` recipe |
| `llm-runner` | no `install` recipe |
| `llm-templating-engine` | no `install` recipe |
| `opencode-transcripts` | no `install` recipe |
| `ai-prompts`, `llm-runner`, `opencode-transcripts` | no `typecheck` recipe |
| `opencode-time-travel-plugin` | no `check` recipe |

---

### Development debris

`.serena/` directories committed in 9 repos: `llm-runner`, `llm-templating-engine`, `opencode-manager`, `opencode-plugin-improved-task`, `opencode-plugin-improved-todowrite`, `opencode-plugin-improved-webtools`, `opencode-plugin-prompt-transformer`, `opencode-time-travel-plugin`, `opencode-zotero-plugin`

Other: `usage-limits/.pytest_cache`, `usage-limits/.ruff_cache`

**Fix:** Add to `.gitignore` and remove from tracking.

---

### Cross-repo local path dependencies

`opencode-plugin-prompt-transformer/src/index.ts` violates the standalone repo requirement:

- `AI_ROOT` defaults to `resolve(_dir, "../../../ai")` — a relative path that implicitly depends on the `ai-prompts` sibling repo being present at a fixed location on disk
- `RESPONSE_TEMPLATE_PATH` is derived from `AI_ROOT`, meaning the plugin cannot be installed or run without a co-located `ai-prompts` clone

**Fix:** Remove the `../../../ai` default. Require `AI_ROOT` or `PROMPTS_DIR` to be set explicitly; throw with a clear error if absent. Document the requirement in the README env var table.

---

### Redundant JSONL log in `opencode-plugin-prompt-transformer`

`src/index.ts` writes a JSONL decision log via `appendLog` / `PROMPT_TRANSFORMER_LOG_PATH`. The tier and reasoning are already rendered into the injected message via the Jinja template (which receives `tier` as a template variable). The log duplicates data already present in parseable form in the transcript.

`tests/behavior/run.sh` reads the tier from this log rather than parsing the transcript, which is the wrong data source — the transcript is the canonical output of a session.

**Fix:** Remove `appendLog`, `LOG_PATH`, and `PROMPT_TRANSFORMER_LOG_PATH`. Update `run.sh` to extract the tier from the rendered template metadata in the transcript output instead.

---

### Missing GitHub Actions workflows

- `llm-runner`
- `llm-templating-engine`
- `opencode-transcripts`
- `zotero` (skills repo)
