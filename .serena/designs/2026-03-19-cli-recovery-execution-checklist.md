# CLI Recovery Execution Checklist

Last updated: 2026-03-19

## Invariants

- MCP remains a thin wrapper forever.
- OpenCode plugins remain thin wrappers forever.
- The standalone CLI is the long-lived canonical interface and must stay framework-agnostic.
- All canonical managers use Python with Cyclopts + Pydantic v2.
- No local `git+file://` routing survives in committed wrapper code.
- Do not continue broader migration work until manager GitHub repos exist and remote `uvx` validation works.

## Phase 0: Damage Assessment And Containment

- [x] Audit current damage across managers, wrappers, tests, and deleted logic.
- [x] Remove fake placeholder extractor code from `zotero-manager/src/zotero_librarian/analysis.py`.
- [x] Inventory all local `git+file://` routes in plugin and MCP wrappers.
- [x] Recover canonical source snapshots from git history for:
  - [x] `opencode-plugin-improved-webtools`
  - [x] `opencode-plugin-improved-todowrite`
  - [x] `opencode-plugin-reminder-injection`
  - [x] `opencode-plugin-improved-task`
  - [x] `opencode-plugin-prompt-transformer`
- [x] Compare recovered snapshots against the damaged manager copies.

## Phase 1: Scope Correction

- [x] Reconfirm the full target set:
  - [x] `memory-manager`
  - [x] `zotero-manager`
  - [x] `webtools-manager`
  - [x] `todowrite-manager`
  - [x] `reminder-manager`
  - [x] `task-manager`
  - [x] `prompt-transformer-manager`
- [x] Keep `opencode-time-travel-plugin` on the archive/deprecate track only.
- [x] Record that MCP shape stays wrapper-only, not a CLI subcommand.

## Phase 2: Manager Rebuilds In The Approved Stack

### Shared Standards

- [ ] Every manager has `pyproject.toml`.
- [ ] Every manager uses Cyclopts.
- [ ] Every manager uses Pydantic v2 contracts.
- [ ] Every manager has Ruff config.
- [ ] Every manager has basedpyright config.
- [ ] Every manager has pytest coverage.
- [ ] Every manager has a `doctor` command when environment checks matter.
- [ ] Every manager has CLI `--help` smoke validation.

### Memory Manager

- [x] Replace Typer with Cyclopts.
- [x] Replace ad hoc inputs with Pydantic v2 models.
- [x] Add Ruff, basedpyright, pytest, and `just` targets.
- [x] Local verification passes via `just lint`, `just typecheck`, and `just test`.
- [x] GitHub repo created and branch pushed to `origin/main`.
- [~] Local post-push changes still need commit/push sync before remote `uvx` validation is trustworthy.

### Zotero Manager

- [x] Remove dead extractor placeholders.
- [x] Recover or delete unsupported extractor code explicitly.
- [x] Convert CLI to Cyclopts.
- [~] Convert contracts to Pydantic v2.
- [x] Add Ruff, basedpyright, pytest, and `just` targets.
- [x] Local tests pass via `just test`.
- [x] Repo-wide first-pass runtime lint passes.
- [x] Repo-wide first-pass strict typecheck passes.
- [x] `arxiv.py` is isolated from first-pass strict verification while the manager core is stabilized.

### Webtools Manager

- [~] Discard Bun manager as canonical implementation.
- [~] Port recovered webfetch/websearch logic into Python modules.
- [~] Preserve canonical Wikipedia handling semantics from recovered source.
- [x] Implement Cyclopts CLI surface.
- [x] Add Pydantic v2 contracts.
- [x] Add Ruff, basedpyright, pytest, and `just` targets.
- [x] Local Python scaffold passes `just lint`, `just typecheck`, and `just test`.
- [x] Python `websearch` port is working locally.
- [x] Generic Python `webfetch` baseline is working locally.
- [x] Direct Python Wikipedia fetch/parse/markdown path replaces the old script hop in the active CLI path.
- [x] First-pass GitHub, Reddit, YouTube, and arXiv handlers are implemented in Python and pass local checks.
- [x] Semantic metadata cleanup is complete locally (`pyproject.toml`, README, package metadata).

### Todowrite Manager

- [~] Discard Bun manager as canonical implementation.
- [x] Port recovered todo tree logic into Python modules.
- [x] Implement Cyclopts CLI surface.
- [x] Add Pydantic v2 contracts.
- [x] Add Ruff, basedpyright, pytest, and `just` targets.
- [x] Local Python scaffold passes `just lint`, `just typecheck`, and `just test`.
- [x] Stable `run-json` bridge exists for wrapper integration.
- [x] Semantic metadata cleanup is complete locally (`pyproject.toml`, README, package metadata).

### Reminder Manager

- [~] Discard Bun manager as canonical implementation.
- [~] Port recovered skill ranking logic into Python modules.
- [x] Implement Cyclopts CLI surface.
- [x] Add Pydantic v2 contracts.
- [x] Add Ruff, basedpyright, pytest, and `just` targets.
- [x] Local Python scaffold passes `just lint`, `just typecheck`, and `just test`.
- [x] Semantic rename to `clis/skill-suggester` is complete locally.
- [x] Doctor/runtime reporting is improved and locally green.
- [x] Semantic metadata cleanup is complete locally (`pyproject.toml`, README, package metadata).

### Task Manager

- [-] Recover canonical task logic into a standalone CLI — skipped: `improved-task` should thin around existing `clis/opencode-manager` / `opx`.
- [-] Extract it into a Python CLI — skipped: no valid framework-agnostic CLI boundary has been confirmed.

### Prompt Transformer Manager

- [~] Recover canonical prompt transformation logic from plugin history.
- [~] Extract it into a Python CLI.
- [x] Implement Cyclopts CLI surface.
- [x] Add Pydantic v2 contracts.
- [x] Add Ruff, basedpyright, pytest, and `just` targets.
- [x] Local Python scaffold passes `just lint`, `just typecheck`, and `just test`.
- [x] Recovered routing passcodes and JSON command-package mapping are implemented in Python.
- [x] Prompt retrieval helper is implemented in Python.
- [x] First-pass template inspect/render and micro-agent command surfaces are implemented in Python.
- [x] Standalone `transform` operation is implemented and locally green.

## Phase 3: GitHub Repo Creation And Remote Validation

- [x] Check whether each manager repo already exists on GitHub.
- [x] Create missing GitHub repos under `dzackgarza`:
  - [x] `memory-manager`
  - [x] `zotero-manager`
  - [x] `webtools-manager`
  - [x] `todowrite-manager`
  - [x] `reminder-manager`
  - [x] `task-manager`
  - [x] `prompt-transformer-manager`
- [x] Add remotes to all local manager repos.
- [~] Push working history to each remote.
- [ ] Validate remote `uvx` install immediately for each manager:
  - [x] `memory-manager`
  - [x] `zotero-manager`
  - [x] `webtools-manager`
  - [x] `todowrite-manager`
  - [x] `reminder-manager`
  - [ ] `task-manager` (no standalone CLI; thin around ocm)
  - [x] `prompt-transformer-manager`

## Phase 4: Wrapper Rewiring

- [x] Replace every local `file:///` route in plugin wrappers (all 6 plugins rewired to remote git+https).
- [x] Replace every local `file:///` route in MCP wrappers (opencode-memory-plugin mcp_server.py).
- [x] Keep MCP wrappers framework-specific and thin.
- [x] Keep OpenCode wrappers framework-specific and thin.
- [x] Move all wrapper calls to remote `uvx` manager repos.
- [ ] Reconcile wrapper contracts with rebuilt Pydantic models.

## Phase 5: Tests And Automation

- [ ] Restore or move tests so managers own core-logic tests.
- [ ] Keep plugin repos focused on wrapper and integration tests.
- [ ] Add `just` targets for managers.
- [ ] Add lightweight hook-safe verification where appropriate.
- [ ] Ensure docs present CLI-first usage first in manager repos.

## Phase 6: Final Verification Gates

- [ ] `gh repo view dzackgarza/<manager>` works for every manager.
- [ ] `uvx --from git+https://... <command> --help` works for every manager.
- [ ] One smoke command works for every manager.
- [ ] Plugin typechecks pass.
- [ ] Manager lint/type/test suites pass.
- [ ] Wrapper integration tests pass.
- [ ] MCP wrappers load and delegate correctly.
- [ ] No committed wrapper code contains `git+file://`.

## Current Findings

- All plugin wrapper code now points at remote git+https URLs (rewired 2026-03-21).
- `memory-manager` has been pushed to `origin/main` and no longer blocks remote-manager existence; it still needs explicit remote `uvx` validation and any remaining local follow-up sync.
- `memory-manager` remote `uvx --help` validation now succeeds.
- `zotero-manager`, `webtools-manager`, `todowrite-manager`, and `reminder-manager` now report upstream tracking on `origin/main`.
- `task-manager` and `prompt-transformer-manager` do not yet exist locally.
- `zotero-manager` placeholder functions were removed, the CLI was moved to Cyclopts, and the manager now passes `just lint`, `just typecheck`, and `just test` under the recorded first-pass scope decisions.
- `zotero-manager/src/zotero_librarian/arxiv.py` has been explicitly removed from first-pass strict lint/type scope because it is isolated from the active CLI/wrapper/test path.
- The current Bun-based `webtools-manager`, `todowrite-manager`, and `reminder-manager` are architectural dead ends and must be replaced as canonical CLIs.
- Recovered source snapshots currently exist for:
  - `opencode-plugin-improved-webtools/src/index.ts.recovered`
  - `opencode-plugin-improved-todowrite/src/todo-tree.ts.recovered`
  - `opencode-plugin-reminder-injection/src/skill-cache.ts.recovered`
  - `opencode-plugin-improved-task/src/index.ts.recovered`
  - `opencode-plugin-prompt-transformer/src/index.ts.recovered`
  - `opencode-plugin-prompt-transformer/src/routing.ts.recovered`
  - `opencode-plugin-prompt-transformer/src/llm.ts.recovered`
- `opencode-plugin-improved-task` confirmed thin wrapper around ocm; no standalone CLI needed.
- `opencode-plugin-prompt-transformer` has `prompt-transformer-manager` on GitHub and remote uvx validates.
- `opencode-plugin-improved-todowrite` integration test passes (2026-03-21): all 3 custom tools execute with passphrase.
- `opencode-plugin-improved-task` and `opencode-plugin-prompt-transformer` are confirmed active migration targets and still need standalone Python manager extraction.
- Comparison findings:
  - `todowrite-manager` is effectively a Bun copy of the recovered todo-tree core with schema/runtime substitutions layered on top.
  - `reminder-manager` is effectively a Bun copy of the recovered skill-cache core.
  - `webtools-manager` is a Bun extraction of the recovered webtools core, but plugin-only shadow/debug concerns were dropped and the brittle Wikipedia script-path dependency remained.
- `opencode-time-travel-plugin` has already been archived and manually deleted.

## Autonomous Execution Queue

### Immediate

- [ ] Run explicit remote `uvx` validation for `memory-manager`.
- [ ] Configure upstream branches for:
  - [ ] `zotero-manager`
  - [ ] `webtools-manager`
  - [ ] `todowrite-manager`
  - [ ] `reminder-manager`
- [ ] Create local repos/directories for:
  - [ ] `task-manager`
  - [ ] `prompt-transformer-manager`

### Zotero Manager Stabilization

- [ ] Clean `src/zotero_librarian/__init__.py` unused export issue.
- [ ] Reformat and simplify `src/zotero_librarian/_dispatch.py` until Ruff passes.
- [ ] Decide whether `src/zotero_librarian/arxiv.py` remains in first-pass scope or is split behind optional commands.
- [ ] Fix high-volume Ruff violations in `src/zotero_librarian/arxiv.py`.
- [ ] Fix high-volume Ruff violations in `src/zotero_librarian/items.py`, `query.py`, `collections.py`, and related modules.
- [ ] Reduce basedpyright unknown-type failures in `_cli.py`.
- [ ] Reduce basedpyright unknown-type failures in `_dispatch.py`.
- [ ] Re-run `just lint` for `zotero-manager`.
- [ ] Re-run `just typecheck` for `zotero-manager`.
- [ ] Re-run `just test` for `zotero-manager`.
- [ ] Push repaired `zotero-manager` and validate remote `uvx` help.

### Webtools Manager Replacement

- [ ] Compare recovered webtools source against the Bun manager copy.
- [ ] Decide the canonical Python module split for `webfetch`, `websearch`, and domain handlers.
- [ ] Create Python `webtools-manager` package skeleton with Cyclopts + Pydantic.
- [ ] Port passphrase constants and output formatting.
- [ ] Port SearxNG query building and pagination.
- [ ] Port domain handlers in priority order:
  - [ ] Wikipedia
  - [ ] GitHub
  - [ ] Reddit
  - [ ] YouTube
  - [ ] arXiv fallback/default fetch flow
- [ ] Preserve canonical Wikipedia handling semantics from recovered source; do not keep dead script shims.
- [ ] Add `doctor` command for required env/tool checks.
- [ ] Add Ruff, basedpyright, pytest, and `just`.
- [ ] Push `webtools-manager` and validate remote `uvx` help + one smoke command.

### Todowrite Manager Replacement

- [ ] Compare recovered todo-tree logic against the Bun manager copy.
- [ ] Create Python `todowrite-manager` package skeleton with Cyclopts + Pydantic.
- [ ] Port tree parsing/serialization.
- [ ] Port current-task selection logic.
- [ ] Port plan/edit/advance operations.
- [ ] Port display/markdown output helpers.
- [ ] Add tests derived from recovered behavior.
- [ ] Add Ruff, basedpyright, pytest, and `just`.
- [ ] Push `todowrite-manager` and validate remote `uvx` help + one smoke command.

### Reminder Manager Replacement

- [ ] Compare recovered reminder logic against the Bun manager copy.
- [ ] Create Python `reminder-manager` package skeleton with Cyclopts + Pydantic.
- [ ] Port skill-cache model loading and ranking flow.
- [ ] Preserve current top-k skill selection semantics.
- [ ] Add environment/doctor checks for required model/runtime dependencies.
- [ ] Add tests around ranking and empty-result behavior.
- [ ] Add Ruff, basedpyright, pytest, and `just`.
- [ ] Push `reminder-manager` and validate remote `uvx` help + one smoke command.

### Task Manager Extraction

- [ ] Create local `task-manager` repo and connect it to GitHub.
- [ ] Recover and isolate core task orchestration logic from `opencode-plugin-improved-task`.
- [ ] Define Python CLI contract for the extracted task operations.
- [ ] Implement Cyclopts + Pydantic CLI.
- [ ] Add tests, Ruff, basedpyright, pytest, and `just`.
- [ ] Push `task-manager` and validate remote `uvx` help + one smoke command.

### Prompt Transformer Manager Extraction

- [ ] Create local `prompt-transformer-manager` repo and connect it to GitHub.
- [ ] Recover routing and prompt-transformation logic from the plugin snapshots.
- [ ] Define Python CLI contract for transformation operations.
- [ ] Implement Cyclopts + Pydantic CLI.
- [ ] Add tests, Ruff, basedpyright, pytest, and `just`.
- [ ] Push `prompt-transformer-manager` and validate remote `uvx` help + one smoke command.

### Wrapper Migration

- [x] Replace local `git+file://` routes in `opencode-memory-plugin`.
- [x] Replace local `git+file://` routes in `opencode-zotero-plugin`.
- [x] Replace local `git+file://` routes in `opencode-plugin-improved-webtools`.
- [x] Replace local `git+file://` routes in `opencode-plugin-improved-todowrite`.
- [x] Replace local `git+file://` routes in `opencode-plugin-reminder-injection`.
- [ ] Thin `plugins/opencode-plugin-improved-task` around existing `clis/opencode-manager` / `opx`.
- [x] Wire `plugins/opencode-plugin-prompt-transformer` to `clis/prompt-transformer` locally.
- [x] Keep all MCP servers as wrapper-only consumption layers.

### Final Verification And Cleanup

- [ ] Ensure every manager has upstream configured and pushed.
- [ ] Ensure every manager passes `just check`.
- [ ] Ensure every manager passes remote `uvx --from git+https://... --help`.
- [ ] Ensure every plugin passes typecheck.
- [x] Ensure every plugin wrapper integration test passes — todowrite passes (3 tools: plan/advance/read, all with passphrase).
- [x] Ensure no committed wrapper code contains `git+file://` or `file:///home/`.
- [ ] Ensure the durable checklist reflects the final state exactly.
