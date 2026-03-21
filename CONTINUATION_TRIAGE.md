# Provenance Triage Continuation

## Scope

This file tracks the provenance/blast-radius audit for the plugin-to-CLI extraction work.
It exists because the immediate problem is trust: several "refactors" appear to have
deleted plugin-owned behavior and replaced it with newly written manager code that may
only approximate the original semantics.

## Goal

Build a provenance-based triage plan from git history before trusting current managers
or wrapper green-status claims.

Outputs required:

- per-repo provenance classification
- blast-radius ranking
- recovery/verification priorities
- explicit open gaps that still need history or code comparison

## Current Working Thesis

- `improved-task` is a special case: it should not have been extracted into a fabricated
  standalone manager and instead should thin around `ocm`.
- `webtools`, `reminder-injection`, `todowrite`, `prompt-transformer`, and `zotero`
  all went through extraction/thin-wrapper transitions that need provenance checks.
- `memory` is different: it appears to be an intentional semantic redesign, so it must be
  validated as a product change rather than assumed to be a faithful refactor.

## Evidence Collected

### Repo Pairings

- `plugins/opencode-memory-plugin` -> `clis/memory-manager`
- `plugins/opencode-plugin-improved-task` -> no standalone manager; should thin around `clis/opencode-manager`
- `plugins/opencode-plugin-improved-todowrite` -> `clis/todowrite`
- `plugins/opencode-plugin-improved-webtools` -> `clis/webtools`
- `plugins/opencode-plugin-prompt-transformer` -> `clis/prompt-transformer`
- `plugins/opencode-plugin-reminder-injection` -> `clis/skill-suggester`
- `plugins/opencode-zotero-plugin` -> `clis/zotero-librarian`

### High-Signal Extraction Boundary Commits

- `plugins/opencode-plugin-improved-webtools`:
  - `1cd3b1e` `Refactor improved-webtools as thin bunx wrapper`
  - deleted in-plugin domain handlers and passphrase logic
- `plugins/opencode-plugin-reminder-injection`:
  - `ccf2b73` `Refactor reminder-injection as thin bunx wrapper`
  - deleted `src/skill-cache.ts`
- `plugins/opencode-zotero-plugin`:
  - `bf115cb` `Update opencode-zotero-plugin to use zotero-manager via uvx`
  - deleted embedded Python core and tests from the plugin repo
- `plugins/opencode-plugin-improved-todowrite`:
  - `69ef220` `Complete improved-todowrite refactor as thin bunx wrapper`
- `plugins/opencode-plugin-prompt-transformer`:
  - no single explicit "thin wrapper" commit found yet in this pass, but current plugin
    is a wrapper and recovered snapshots remain in-tree
- `plugins/opencode-plugin-improved-task`:
  - no valid manager extraction target; current trust issue is architectural confusion plus
    test/runtime rewrites

### Recovered Snapshot Availability

- `plugins/opencode-plugin-improved-task/src/index.ts.recovered`
- `plugins/opencode-plugin-improved-todowrite/src/todo-tree.ts.recovered`
- `plugins/opencode-plugin-improved-webtools/src/index.ts.recovered`
- `plugins/opencode-plugin-prompt-transformer/src/index.ts.recovered`
- `plugins/opencode-plugin-prompt-transformer/src/llm.ts.recovered`
- `plugins/opencode-plugin-prompt-transformer/src/routing.ts.recovered`
- `plugins/opencode-plugin-reminder-injection/src/skill-cache.ts.recovered`

No analogous recovered snapshot has been identified yet for:

- `plugins/opencode-memory-plugin`
- `plugins/opencode-zotero-plugin`

### Initial CLI Commit Signals

- `clis/webtools`:
  - `0f328b1` `Initial commit of webtools-manager core logic and CLI`
  - starts with fresh TS manager files, later gains Python path
- `clis/skill-suggester`:
  - `d25e8e0` `Initial commit of reminder-manager core logic and CLI`
  - initial extracted file appears close to recovered plugin logic
- `clis/zotero-librarian`:
  - `a9f693f` `Initial commit of zotero-manager extracted from plugin`
  - provenance better, but plugin lost embedded proof surface
- `clis/todowrite`:
  - `44f7074` `Initial commit of todowrite-manager core logic and CLI`
- `clis/prompt-transformer`:
  - current visible base is a Python checkpoint, suggesting greenfield rewrite risk
- `clis/memory-manager`:
  - current visible base is `Finalize memory-manager structure`, consistent with semantic redesign

### Test Migration Signals

- `webtools`
  - plugin unit tests were explicitly deleted in `7d8d97a` (`Move unit tests to webtools-manager`)
  - current CLI repo now contains:
    - Python tests for domain handlers/core/models
    - TS unit test `tests/unit/searxng-search.test.ts`
    - integration test `tests/integration/webtools-plugin.test.ts`
  - plugin integration tests were heavily rewritten later and now only prove a much smaller surface
- `reminder-injection`
  - plugin unit test `tests/skill-reminder.test.ts` was explicitly deleted in `7ce20a0`
  - CLI repo now contains:
    - restored TS test `tests/skill-reminder.test.ts`
    - Python `tests/test_core.py`
  - plugin regained only a later end-to-end integration test on 2026-03-21
- `zotero`
  - plugin deleted embedded Python tests together with the Python core in `bf115cb`
  - CLI repo contains the migrated Python tests
  - plugin currently has only a static integration config stub, not substantive live proof
- `todowrite`
  - no explicit "move unit tests to manager" commit surfaced in this pass
  - CLI repo contains both:
    - Python `tests/test_core.py`
    - TS unit + integration tests
  - plugin retained integration tests, but they were repeatedly rewritten around harness changes
- `prompt-transformer`
  - plugin test history shows major deletion of classifier/behavior assets at `39a303c`
  - current CLI repo has only a small Python `tests/test_core.py`
  - this suggests substantial proof-surface shrinkage relative to earlier plugin-owned testing
- `memory`
  - plugin retained integration tests throughout the redesign, but those tests were also rewritten
    as the product semantics changed (`recall` removed, SQL list introduced, etc.)
  - CLI repo has only a Python CLI test surface, so plugin-level behavior change must be assessed
    as a redesign, not a pure extraction

### Direct Code Comparison Results

- `reminder-injection`:
  - `plugins/opencode-plugin-reminder-injection/src/skill-cache.ts.recovered`
    and `clis/skill-suggester/src/skill-cache.ts` diff cleanly with no content delta
  - classification: direct carry of the core ranking/cache logic
- `todowrite`:
  - `plugins/opencode-plugin-improved-todowrite/src/todo-tree.ts.recovered`
    and `clis/todowrite/src/todo-tree.ts` are extremely close
  - observed differences are primarily:
    - quote/style normalization
    - `tool.schema` -> `zod` schema translation
    - small import ordering/formatting changes
  - classification: translated but strongly traceable carry
- `webtools`:
  - comparing `plugins/opencode-plugin-improved-webtools/src/index.ts.recovered`
    to `clis/webtools/src/index.ts` shows no direct carry at the entrypoint layer
  - recovered plugin file was a monolithic 1052-line implementation; CLI entrypoint is a
    6-line barrel export while behavior is redistributed across TS and Python files
  - this does not prove semantic loss by itself, but it means provenance must be checked
    module-by-module rather than assuming a faithful file extraction
  - module spot checks:
    - recovered `src/passphrases.ts` matches `clis/webtools/src/passphrases.ts`
    - recovered Reddit handler matches `clis/webtools/src/domains/reddit.ts` exactly
  - revised classification: direct carry for at least some TS modules, but with a
    wrapper/manager architecture rewrite and reduced plugin-owned proof surface
- `prompt-transformer`:
  - comparing recovered TS plugin entrypoint with Python manager core shows clear semantic
    relationship but not a direct extraction
  - constants and tier/passcode concepts are preserved, but implementation is a language-port
    with structural reinterpretation
  - plugin history also shows proof-surface shrinkage:
    - earlier unit test for faux-rule matching existed in plugin history
    - earlier classifier harness docs and assets existed in `tests/classifier/`
    - commit `39a303c` removed large classifier/behavior assets from the plugin repo
    - current CLI repo only has a small Python `tests/test_core.py`
  - classification: translated reinterpretation, not direct carry
- `zotero`:
  - pre-extraction plugin `python/src/zotero_librarian/__init__.py` and current
    `clis/zotero-librarian/src/zotero_librarian/__init__.py` are effectively identical
  - pre-extraction plugin `python/tests/test_tools.py` and current
    `clis/zotero-librarian/tests/test_tools.py` are effectively identical
  - classification: strong evidence of direct relocation of core code and tests into the CLI repo;
    main trust issue is plugin proof-surface shrinkage, not obvious manager hallucination
- `memory`:
  - plugin history shows a real semantic redesign occurred in-plugin before manager trust became relevant
  - `16249ac` still used PostgreSQL/pgvector-backed querying
  - `2ec4d4d` replaced that with a file-based memory design and local CLI mediation
  - current trust issue is therefore not "was the extraction faithful?" but:
    - was the redesign itself correct?
    - does the manager-backed version still prove the intended redesigned behavior?
  - classification: product redesign, not pure refactor

## Preliminary Classification

### Very High Blast Radius

- `webtools`
- `zotero`

### High Blast Radius

- `prompt-transformer`
- `memory`
- `improved-task`

### Medium Blast Radius

- `reminder-injection`
- `todowrite`

## Matrix Snapshot

| Repo Pair | Plugin Core Deleted? | Recovered Snapshot? | Tests Explicitly Moved? | Current Trust |
| --- | --- | --- | --- | --- |
| `improved-webtools` -> `webtools` | Yes | Yes | Yes | Low |
| `improved-webtools` -> `webtools` note | Some TS modules carry exactly; architecture and proof surface changed | | | |
| `reminder-injection` -> `skill-suggester` | Yes | Yes | Yes | Medium-High |
| `zotero-plugin` -> `zotero-librarian` | Yes | No snapshot found | Yes | Medium |
| `improved-todowrite` -> `todowrite` | Functionally yes | Yes | Partial/unclear | Medium-High |
| `prompt-transformer` -> `prompt-transformer` | Wrapperized | Yes | Proof surface shrank | Low-Medium |
| `memory-plugin` -> `memory-manager` | No, but semantics changed | No snapshot found | No clear move; redesign instead | Low |
| `improved-task` -> `opencode-manager` | No valid extraction target | Yes | N/A | Low until re-proven |

## Why The Current "Green" State Is Not Trusted

- Some continuation/docs claim multiple CLIs are locally green, but git history shows
  direct deletion of plugin-owned behavior and tests at extraction boundaries.
- A green CLI test suite does not prove the extracted manager preserved original plugin behavior.
- Wrapper repos often lost their own core-logic proofs after becoming thin wrappers.

## Next Steps

### Immediate

- build a per-repo provenance matrix with:
  - pre-extraction plugin commit
  - extraction commit
  - initial CLI commit
  - current wrapper commit
  - tests removed vs moved vs rewritten
  - recovered snapshot availability
- diff plugin recovered sources against current CLI core for:
  - `webtools`
  - `reminder-injection`
  - `todowrite`
  - `prompt-transformer`
- locate missing provenance anchors for:
  - `zotero`
  - `memory`
- identify whether `webtools` and `prompt-transformer` manager code is a direct carry,
  partial carry, or greenfield reinterpretation at the file/function level
- continue module-level provenance checks for `webtools`
- find pre-redesign anchor for `memory`
- find whether `zotero` plugin still has accessible pre-thin-wrapper source in history that
  can be compared directly to `clis/zotero-librarian`

### After Matrix

- classify each repo as:
  - faithful carry
  - translated but traceable
  - semantic rewrite
  - hallucinated/new behavior
- produce a recovery order based on user-facing risk and proof loss

## Open Questions

- What exact pre-extraction plugin commits should be treated as canonical source-of-truth for
  each repo pair?
- Which plugin-owned tests were deleted outright versus genuinely moved into CLI repos?
- For `prompt-transformer`, which current manager behaviors are direct carries from recovered
  TS logic and which are Python reinterpretations?
- For `memory`, what was the exact last trusted behavior before the product-level redesign?
- For `zotero`, is the CLI extraction faithful enough that the main blast radius is proof loss,
  or were semantics changed materially during extraction?
- For `webtools`, which specific plugin features/proofs were reduced to a smaller wrapper
  contract, and which were actually preserved in the manager?
- For `prompt-transformer`, which deleted classifier/behavior harness assets still matter as
  proof obligations for the current product?
