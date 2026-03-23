# Continuation

This file is the active OSOT for the CI-first proof migration.

## Goal

Use one centralized CI recipe family for this workspace, have repo-local packages inherit from it, and rely on standard OpenCode config discovery instead of manual config or path overrides.

## Active Direction

- CI owns the proof environment.
- Local repos inherit the reusable workflows in this repo instead of carrying bespoke CI logic.
- OpenCode proof runs use normal precedence:
  - global `~/.config/opencode/opencode.json`
  - repo-root `opencode.json`
- Do not use `OPENCODE_CONFIG` or `OPENCODE_CONFIG_DIR` for these repos unless a real documented exception appears.
- Do not use `OPENCODE_TEST_AGENT_NAME` or `OPENCODE_TEST_PROJECT_DIR` as a proof harness shim.
- `just test` is the canonical local test entrypoint, but it does not start or stop `opencode serve`.
- Local debugging starts a repo-local `opencode serve` separately and points tests at it with `OPENCODE_BASE_URL`.

## Historical References

These are retained as background context for why the migration exists:

- [.serena/designs/2026-03-19-cli-recovery-execution-checklist.md](/home/dzack/opencode-plugins/.serena/designs/2026-03-19-cli-recovery-execution-checklist.md)
- [recovery-plan-repair-damaged-r-2026-03-19-approved.md](/home/dzack/.plannotator/plans/recovery-plan-repair-damaged-r-2026-03-19-approved.md)

Additional Claude plan files under `/home/dzack/.claude/plans/` were reviewed in the earlier audit phase and then removed during cleanup. The retired repo-local `CONTINUATION_TRIAGE.md` handoff and the stale Zotero subrepo continuation were also removed after their decisions were folded into this file.

## Canonical CI Templates

The reusable workflow templates that now define the supported CI shapes are:

- [.github/workflows/python-cli-ci.yml](/home/dzack/opencode-plugins/.github/workflows/python-cli-ci.yml)
- [.github/workflows/python-cli-publish.yml](/home/dzack/opencode-plugins/.github/workflows/python-cli-publish.yml)
- [.github/workflows/bun-plugin-ci.yml](/home/dzack/opencode-plugins/.github/workflows/bun-plugin-ci.yml)
- [.github/workflows/bun-plugin-publish.yml](/home/dzack/opencode-plugins/.github/workflows/bun-plugin-publish.yml)

The intended behavior is:

- caller repos only declare `uses: dzackgarza/opencode-plugins/.github/workflows/...@main`
- Python CLI repos inherit shared QC through `OPENCODE_PYTHON_QC_JUSTFILE`
- Bun plugin repos run repo-owned `just` gates directly
- OpenCode live-proof jobs start `opencode serve` from the caller repo checkout so repo-root `opencode.json` is discovered normally

## Adoption Status

### Python CLI repos using centralized workflows

- [clis/opencode-manager/.github/workflows/ci.yml](/home/dzack/opencode-plugins/clis/opencode-manager/.github/workflows/ci.yml)
- [clis/opencode-manager/.github/workflows/publish.yml](/home/dzack/opencode-plugins/clis/opencode-manager/.github/workflows/publish.yml)
- [clis/llm-templating-engine/.github/workflows/ci.yml](/home/dzack/opencode-plugins/clis/llm-templating-engine/.github/workflows/ci.yml)
- [clis/llm-templating-engine/.github/workflows/publish.yml](/home/dzack/opencode-plugins/clis/llm-templating-engine/.github/workflows/publish.yml)
- [clis/llm-runner/.github/workflows/ci.yml](/home/dzack/opencode-plugins/clis/llm-runner/.github/workflows/ci.yml)
- [clis/llm-runner/.github/workflows/publish.yml](/home/dzack/opencode-plugins/clis/llm-runner/.github/workflows/publish.yml)
- [clis/usage-limits/.github/workflows/check.yml](/home/dzack/opencode-plugins/clis/usage-limits/.github/workflows/check.yml)
- [clis/usage-limits/.github/workflows/publish.yml](/home/dzack/opencode-plugins/clis/usage-limits/.github/workflows/publish.yml)

### Bun plugin repos using centralized workflows

- [plugins/opencode-memory-plugin/.github/workflows/ci.yml](/home/dzack/opencode-plugins/plugins/opencode-memory-plugin/.github/workflows/ci.yml)
- [plugins/opencode-memory-plugin/.github/workflows/publish.yml](/home/dzack/opencode-plugins/plugins/opencode-memory-plugin/.github/workflows/publish.yml)
- [plugins/opencode-plugin-improved-task/.github/workflows/ci.yml](/home/dzack/opencode-plugins/plugins/opencode-plugin-improved-task/.github/workflows/ci.yml)
- [plugins/opencode-plugin-improved-task/.github/workflows/publish.yml](/home/dzack/opencode-plugins/plugins/opencode-plugin-improved-task/.github/workflows/publish.yml)
- [plugins/opencode-plugin-improved-todowrite/.github/workflows/ci.yml](/home/dzack/opencode-plugins/plugins/opencode-plugin-improved-todowrite/.github/workflows/ci.yml)
- [plugins/opencode-plugin-improved-todowrite/.github/workflows/publish.yml](/home/dzack/opencode-plugins/plugins/opencode-plugin-improved-todowrite/.github/workflows/publish.yml)
- [plugins/opencode-plugin-improved-webtools/.github/workflows/ci.yml](/home/dzack/opencode-plugins/plugins/opencode-plugin-improved-webtools/.github/workflows/ci.yml)
- [plugins/opencode-plugin-improved-webtools/.github/workflows/publish.yml](/home/dzack/opencode-plugins/plugins/opencode-plugin-improved-webtools/.github/workflows/publish.yml)
- [plugins/opencode-plugin-prompt-transformer/.github/workflows/ci.yml](/home/dzack/opencode-plugins/plugins/opencode-plugin-prompt-transformer/.github/workflows/ci.yml)
- [plugins/opencode-plugin-prompt-transformer/.github/workflows/publish.yml](/home/dzack/opencode-plugins/plugins/opencode-plugin-prompt-transformer/.github/workflows/publish.yml)
- [plugins/opencode-plugin-reminder-injection/.github/workflows/ci.yml](/home/dzack/opencode-plugins/plugins/opencode-plugin-reminder-injection/.github/workflows/ci.yml)
- [plugins/opencode-plugin-reminder-injection/.github/workflows/publish.yml](/home/dzack/opencode-plugins/plugins/opencode-plugin-reminder-injection/.github/workflows/publish.yml)
- [plugins/opencode-zotero-plugin/.github/workflows/ci.yml](/home/dzack/opencode-plugins/plugins/opencode-zotero-plugin/.github/workflows/ci.yml)
- [plugins/opencode-zotero-plugin/.github/workflows/publish.yml](/home/dzack/opencode-plugins/plugins/opencode-zotero-plugin/.github/workflows/publish.yml)

## Repo Contract Decisions Captured In Code

### Justfiles and `.envrc`

- plugin repos no longer source workspace `.testrc`
- plugin repos use `source_up_if_exists` instead of assuming a parent env file exists
- plugin `justfile`s no longer spin up or tear down a top-level sandbox
- package.json test/typecheck/check scripts point to `just --justfile justfile ...`

### Repo-root `opencode.json`

Repo-root `opencode.json` is now the canonical proof config for every migrated plugin repo:

- [plugins/opencode-memory-plugin/opencode.json](/home/dzack/opencode-plugins/plugins/opencode-memory-plugin/opencode.json)
- [plugins/opencode-plugin-improved-task/opencode.json](/home/dzack/opencode-plugins/plugins/opencode-plugin-improved-task/opencode.json)
- [plugins/opencode-plugin-improved-todowrite/opencode.json](/home/dzack/opencode-plugins/plugins/opencode-plugin-improved-todowrite/opencode.json)
- [plugins/opencode-plugin-improved-webtools/opencode.json](/home/dzack/opencode-plugins/plugins/opencode-plugin-improved-webtools/opencode.json)
- [plugins/opencode-plugin-prompt-transformer/opencode.json](/home/dzack/opencode-plugins/plugins/opencode-plugin-prompt-transformer/opencode.json)
- [plugins/opencode-plugin-reminder-injection/opencode.json](/home/dzack/opencode-plugins/plugins/opencode-plugin-reminder-injection/opencode.json)
- [plugins/opencode-zotero-plugin/opencode.json](/home/dzack/opencode-plugins/plugins/opencode-zotero-plugin/opencode.json)

Important details:

- `plugin-proof` remains the standard agent name for ordinary plugin proofs
- repo-local `agent.plugin-proof` overrides are used only to specialize prompt/description/permissions through normal config precedence
- `opencode-plugin-improved-task` keeps repo-local custom agents because it proves both `improved_task` and shadow `task`
- redundant `tests/integration/test-opencode.json` fixtures were deleted from:
  - `opencode-memory-plugin`
  - `opencode-plugin-improved-todowrite`
  - `opencode-plugin-prompt-transformer`

### Integration harness cleanup

The plugin integration suites no longer depend on stale harness env vars:

- `OPENCODE_TEST_AGENT_NAME` removed from plugin tests in favor of fixed repo-owned agent names
- `OPENCODE_TEST_PROJECT_DIR` removed from plugin tests in favor of running from repo root
- comments claiming `just test` starts or tears down the OpenCode server were removed

The affected tests are:

- [plugins/opencode-memory-plugin/tests/integration/memory-plugin.test.ts](/home/dzack/opencode-plugins/plugins/opencode-memory-plugin/tests/integration/memory-plugin.test.ts)
- [plugins/opencode-plugin-improved-task/tests/integration/task-plugin.test.ts](/home/dzack/opencode-plugins/plugins/opencode-plugin-improved-task/tests/integration/task-plugin.test.ts)
- [plugins/opencode-plugin-improved-todowrite/tests/integration/todowrite-plugin.test.ts](/home/dzack/opencode-plugins/plugins/opencode-plugin-improved-todowrite/tests/integration/todowrite-plugin.test.ts)
- [plugins/opencode-plugin-improved-webtools/tests/integration/webtools-plugin.test.ts](/home/dzack/opencode-plugins/plugins/opencode-plugin-improved-webtools/tests/integration/webtools-plugin.test.ts)
- [plugins/opencode-plugin-prompt-transformer/tests/integration/prompt-router.test.ts](/home/dzack/opencode-plugins/plugins/opencode-plugin-prompt-transformer/tests/integration/prompt-router.test.ts)
- [plugins/opencode-plugin-reminder-injection/tests/integration/reminder-injection.test.ts](/home/dzack/opencode-plugins/plugins/opencode-plugin-reminder-injection/tests/integration/reminder-injection.test.ts)
- [plugins/opencode-zotero-plugin/tests/integration/zotero-plugin.test.ts](/home/dzack/opencode-plugins/plugins/opencode-zotero-plugin/tests/integration/zotero-plugin.test.ts)

## Validation Completed

- `just --list` succeeds for the root `justfile`
- `just --list` succeeds for all migrated plugin `justfile`s
- root reusable workflow YAML parses
- plugin caller workflow YAML parses
- repo-root plugin `opencode.json` files parse as JSON
- modified MCP server Python files compile
- migrated plugin TypeScript suites typecheck through repo-local `just typecheck`

## Remaining Blockers

- The reusable workflow changes must land before the caller workflow updates can pass in GitHub Actions.
- The decisive proof is the first clean CI run with real secrets and auth, not local static validation.
- If the first CI run fails, inspect these first:
  - repo-root `opencode.json` discovery from the caller checkout
  - `OPENCODE_AUTH_JSON` secret materialization
  - proof-agent visibility through standard global-plus-project config merge

## Do Not Reintroduce

- no sandbox startup or teardown recipes for CI
- no `.testrc`-driven proof harness
- no `OPENCODE_CONFIG` / `OPENCODE_CONFIG_DIR` overrides for this migration
- no repo-local duplicate workflow logic when a centralized reusable workflow already exists
- no dead `tests/integration/test-opencode.json` sidecar configs when the repo-root `opencode.json` owns the proof contract
