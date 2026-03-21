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

- **[BLOCKED on PR #19 merge in dzackgarza/opencode-manager]**
  - Both `prompt-transformer` and `todowrite` integration tests use `ocm begin-session`.
  - Local `clis/opencode-manager` has the fix (`submit_prompt_no_wait`).
  - Published GitHub main still uses blocking `submit_prompt` → tests fail live.
  - PR #19 needs merge before either test can be validated green.
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

### 1. Merge PR #19 in dzackgarza/opencode-manager

- The fix (`submit_prompt_no_wait`) is already in the local repo at `clis/opencode-manager`.
- Merging PR #19 unblocks live `just test` validation for both prompt-transformer and todowrite.

### 2. Run `just test` for both fixed plugins (after PR #19 merge)

- `plugins/opencode-plugin-prompt-transformer`
- `plugins/opencode-plugin-improved-todowrite`

### 3. Re-audit `plugins/opencode-plugin-improved-task`

- Treat it as a thin wrapper over the existing manager CLI surface (`ocm`).
- Do not create a new standalone CLI for it.

### 4. Final sweep

- Run all plugin typechecks.
- Grep for `git+file://` to confirm no regressions.
- Update the durable checklist to reflect final state.

## Current Todo List

- **[BLOCKED]** Merge PR #19 in `dzackgarza/opencode-manager` to unblock live test validation.
- Run `just test` for `prompt-transformer` and `todowrite` after PR #19 merge.
- Re-audit `plugins/opencode-plugin-improved-task` around real `ocm` surface.
- Run final plugin typechecks and grep for `git+file://` in committed code.

## Notes

- Do not spend more time on fake standalone extraction for `improved-task`.
- Do not reintroduce `git+file://` in wrapper code.
- If a repo rename changes package metadata again, expect local venv wrapper/shebang churn; rebuilding `.venv` may be necessary.
