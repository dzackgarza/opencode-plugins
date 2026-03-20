# Continuation

## Current Situation

The workspace has been reorganized into:

- `plugins/` - OpenCode plugins and MCP wrappers
- `clis/` - standalone CLI/tool repos

Valid standalone CLI targets:

- `plugins/opencode-memory-plugin` -> `clis/memory-manager`
- `plugins/opencode-zotero-plugin` -> `clis/zotero-librarian`
- `plugins/opencode-plugin-improved-webtools` -> `clis/webtools`
- `plugins/opencode-plugin-improved-todowrite` -> `clis/todowrite`
- `plugins/opencode-plugin-prompt-transformer` -> `clis/prompt-transformer`
- `plugins/opencode-plugin-reminder-injection` -> `clis/skill-suggester`

Important correction:

- `plugins/opencode-plugin-improved-task` should not map to a fabricated standalone CLI.
- It should thin around the existing OpenCode manager CLI surface.
- The old local `clis/delegate-task` extraction was invalid and has been retired.

## Existing Plans / References

- Durable execution checklist:
  - `.serena/designs/2026-03-19-cli-recovery-execution-checklist.md`
- Most recently accepted revised plan:
  - `/home/dzack/.plannotator/plans/recovery-plan-repair-damaged-r-2026-03-19-approved.md`
- Earlier memory-plugin design doc:
  - `.serena/designs/2026-03-18-memory-plugin-refactor-design.md`

## Current Local State

Locally green CLI repos:

- `clis/webtools`
- `clis/todowrite`
- `clis/skill-suggester`
- `clis/prompt-transformer`
- `clis/memory-manager`
- `clis/zotero-librarian` (under recorded first-pass scope decisions)

Locally updated plugin wrappers:

- `plugins/opencode-memory-plugin`
- `plugins/opencode-zotero-plugin`
- `plugins/opencode-plugin-improved-webtools`
- `plugins/opencode-plugin-improved-todowrite`
- `plugins/opencode-plugin-reminder-injection`
- `plugins/opencode-plugin-prompt-transformer`

Local wrapper routing status:

- live wrapper code in `plugins/` no longer uses `git+file://`
- local development wrapper paths now use `file:///home/dzack/opencode-plugins/clis/...`

## Known Local Blockers

These are the main remaining local issues before publication/remote validation:

- `plugins/opencode-plugin-prompt-transformer/tests/integration/prompt-router.test.ts`
  - still fails against the current OpenCode manager workflow
  - previous assumptions about `opx-session` are stale
  - user noted that upstream renamed `opx` usage toward `ocm` and added functionality
- `plugins/opencode-plugin-improved-todowrite/tests/integration/todowrite-plugin.test.ts`
  - still fails in live proof mode with `FAIL:PROOF_NOT_POSSIBLE`
  - likely a tool visibility / session behavior issue rather than CLI-core logic
- `plugins/opencode-plugin-improved-task`
  - still needs a clean local audit/rewrite around the real `ocm` manager surface
  - do not create a new standalone CLI for it

## Git Pushes Still Needed

These repos have local work that should eventually be pushed:

- root repo `opencode-plugins` (for checklist / continuation docs)
- `clis/webtools`
- `clis/todowrite`
- `clis/skill-suggester`
- `clis/prompt-transformer`
- `plugins/opencode-plugin-prompt-transformer`
- `plugins/opencode-plugin-reminder-injection`
- `plugins/opencode-plugin-improved-todowrite`
- `plugins/opencode-plugin-improved-webtools`
- `plugins/opencode-memory-plugin`
- `plugins/opencode-zotero-plugin`

Probably not needed yet:

- `plugins/opencode-plugin-improved-task` until the `ocm`-based local rewrite is done
- `clis/opencode-manager` unless local changes are made there

## Immediate Next Actions

Do these next, in order:

### 1. Update the manager-integration assumptions from `opx` to `ocm`

- Audit the current `clis/opencode-manager` public workflow surface.
- Determine whether `ocm` is a renamed binary, an alias, or a new command surface.
- Update the durable checklist to reflect the current manager CLI name and workflow.

### 2. Fix the two blocked plugin integration proofs

- `plugins/opencode-plugin-prompt-transformer/tests/integration/prompt-router.test.ts`
  - rewrite around the current manager workflow instead of the removed `opx-session` assumptions
  - verify that the plugin proof still tests true last-mile behavior, not CLI internals
- `plugins/opencode-plugin-improved-todowrite/tests/integration/todowrite-plugin.test.ts`
  - verify tool visibility and exact tool-call proof path under the current manager workflow

### 3. Re-audit `plugins/opencode-plugin-improved-task`

- treat it as a thin wrapper over the existing manager CLI surface (`ocm` / current `opencode-manager`)
- identify whether any purely local helper logic still needs extraction
- do not recreate any standalone CLI for it

### 4. Re-run local plugin verification after the manager/workflow corrections

- plugin typechecks
- last-mile integration tests
- grep to confirm no wrapper code regressed to `git+file://`

### 5. Only near the end, do publication and remote validation

- push updated CLI repos
- run remote `uvx --from git+https://... --help`
- run one smoke command per CLI
- then push updated plugin repos if needed

## Current Todo List

- Keep `.serena/designs/2026-03-19-cli-recovery-execution-checklist.md` synchronized with actual repo state after each significant change
- Repair `ocm`-dependent last-mile integration proofs for:
  - `plugins/opencode-plugin-prompt-transformer`
  - `plugins/opencode-plugin-improved-todowrite`
- Re-audit `plugins/opencode-plugin-improved-task` around the real manager CLI surface and thin it accordingly
- Publish updated CLI repos and run remote `uvx` validations near the end
- Run final plugin typechecks, wrapper integration tests, and grep for `git+file://`

## Notes

- Do not spend more time on fake standalone extraction for `improved-task`.
- Do not reintroduce `git+file://` in wrapper code.
- If a repo rename changes package metadata again, expect local venv wrapper/shebang churn; rebuilding `.venv` may be necessary.
