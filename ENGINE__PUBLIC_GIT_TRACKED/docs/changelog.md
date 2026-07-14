# CHAIN Changelog

Project changelog. Reverse chronological. Maintained as readable project memory: what
changed, what was explored, and why it mattered — not a commit log. Git history
already holds the granular record; this file is the curated account.

Add rough entries here during meaningful work (see `chain/changelog_sync.py`'s module
docstring for the format). Run `python3 -m chain.changelog_sync` to consolidate them
into readable threads.


<!-- changelog-processed-through: fc52b5a0b82f7e928c41280e293187294228dc68 -->
---

## 2026-07-13 — Changelog capture became mandatory, synthesis lost its API dependency

- Added `CLAUDE.md` (this repo had none) requiring every coding agent — Claude Code,
  Codex, or otherwise — to add a rough `docs/changelog.md` entry in the same turn as
  any meaningful change, or state why none is needed. This was previously only a soft
  pointer in `README.md`, not a completion requirement, and rough entries were not
  being captured automatically as a result.
- Added `AGENTS.md` so Codex finds the same rule without a duplicated copy.
- Removed the direct Anthropic API call from `chain/changelog_sync.py`. The original
  design assumed unattended, standalone synthesis (mirroring an external reference
  implementation), but the actual workflow asks an active Claude Code or Codex session
  to perform synthesis itself. The module now only gathers Git evidence and manages
  the deterministic structure/marker; no API key is needed anywhere in this repo.
- Started the same visible ENGINE/PRIVATE/READY-TO-REVIEW restructure applied to
  JAIL. Batch 1 (this entry): created `PRIVATE__YOUR_FILES_GITIGNORED/` and moved
  `chain.config.local.yaml` into it (`chain/config.py`'s `LOCAL_CONFIG` updated to
  match); added visible symlinks for every canon reference and every configured
  source, plus one for `chain_home/library` — so a person can see what CHAIN actually
  reads without leaving the repo. Fixed a stale `sources.application` path left over
  from JAIL's own restructure (still pointed at JAIL's pre-restructure `04-TAILOR`).
  `.gitignore` now ignores the whole `PRIVATE__YOUR_FILES_GITIGNORED/` root instead of
  a bare `chain.config.local.yaml` line; updated `test_path_safety.py`'s firewall
  assertion to match. Added design principle 4 to `docs/architecture.md` ("Visible
  structure over hidden convenience") capturing why symlinks are now a preferred
  pattern here, not just an implementation shortcut.
- Batch 2: retired `chain_home/workspace/` as a concept entirely. Investigated the
  migration first (asked: which files, which references, is `pieces.csv` the only
  thing pointing at them, any remaining reason to keep it under `chain_home`) — found
  exactly 3 stale references, all in `pieces.csv`'s `final_text_path`, nothing else.
  `__READY_TO_REVIEW__PRIVATE_GITIGNORED/` is now the fixed, non-configurable canonical
  home for generated output (`chain/config.py`'s `workspace_dir` now derives from a
  new `REVIEW_DIR` constant instead of `chain_home`); `chain_home` shrinks to machine
  state (`cache/`, `state/`) plus the durable library. Physically moved the two real
  historical runs out of `~/.chain/workspace/` into the repo (rather than leaving
  history stranded in the old location) and rewrote `pieces.csv`'s 3 paths to match;
  deleted the now-empty `~/.chain/workspace/`. Extended `path_safety.py`'s
  `IGNORED_WRITABLE_PREFIXES` and `config.py`'s firewall check to cover the new root
  explicitly (it no longer inherits safety from being nested under `chain_home`).
  Revised design principle 2 (dropped the now-false "Workspace is intentionally
  disposable" framing) and extended principle 4 with the decision rule: prefer
  legibility for a new user over preserving historical implementation, unless
  migration cost is genuinely significant. Rewrote `docs/architecture.md`'s "Where
  things live" section (was "two ideas, not three" — now three), plus stale
  `chain_home/workspace` mentions in `docs/privacy.md`, `docs/sources.md`,
  `docs/packet.md`, `chain.config.example.yaml` (also fixed a stale `cp
  chain.config.local.yaml`-to-root instruction left over from Batch 1), `produce.py`,
  and both `examples/sample-*-packet.md` files. `chain doctor` and the full suite
  (119 tests) confirm clean after the move.
- Batch 3: moved `chain/`, `canon/`, `docs/`, `examples/`, `tests/` under
  `ENGINE__PUBLIC_GIT_TRACKED/` as one atomic `git mv` (101 files, all clean renames).
  Root-required files (`README.md`, `CLAUDE.md`, `AGENTS.md`, `.claude/`, `.codex/`,
  `chain.config.example.yaml`, `pyproject.toml`, `.gitignore`) stayed put. Fixed the
  code this broke: `chain/config.py`'s `REPO_ROOT` gained a third `.parent` (chain.
  config.example.yaml and the PRIVATE/READY-TO-REVIEW roots stay at true root, not
  nested); `changelog_sync.py`'s `DOCS_DIR` and `changelog_core.py`'s
  `_SYNTHESIS_MAINTENANCE_PATHS`/`startswith` check now use `ENGINE__PUBLIC_GIT_TRACKED/`-
  prefixed paths, matching what `git diff` actually reports post-move; `pyproject.toml`
  gained a `package-dir` mapping and an updated `testpaths`. `test_path_safety.py`
  needed a dual anchor (`REPO` = the new ENGINE level, self-correcting; `TOP_ROOT` =
  `REPO.parent`, the true root — `.gitignore`, `.chain/`, and the PRIVATE/READY-TO-
  REVIEW roots all still live at `TOP_ROOT`, not under ENGINE) since not everything the
  firewall checks moved together.
  Established one convention for the whole repo: run `chain` commands from
  `ENGINE__PUBLIC_GIT_TRACKED/` (documented in the README quickstart, `CLAUDE.md`, both
  `chain-intake` agent files, and `chain/changelog_sync.py`'s docstring) — this is also
  why the demo/persona example configs' `chain_home: ./.chain/...` needed to become
  `../.chain/...` (the true-root `.chain/` is now one level up from where these
  configs are loaded and used), while their `sources:`/`voice_spec` paths stayed bare
  (`examples/...` is a direct sibling from inside ENGINE, no prefix needed — caught and
  reverted an over-correction here after `chain.intake` on the demo persona silently
  returned 0 files for a source I'd double-prefixed by mistake). `tests/test_intake.py`
  had the same fragility for real: `PersonaTests`/`ManifestTests` load persona configs
  by absolute config-file path but the *values inside* those configs are CWD-relative,
  so they silently classified everything as maturity level 3 (nothing found) when the
  suite was run from the true root instead of ENGINE. Fixed at the source
  (`persona_config()` now resolves relative source/canon paths to absolute
  immediately after loading) rather than requiring a specific invocation directory —
  the suite now passes identically run from either location.
  Also fixed, opportunistically, while touching these same files: `chain-intake.md`/
  `.toml` both still said "NEVER write user content inside the CHAIN repo," stale since
  Batch 1 introduced the in-repo (gitignored) `PRIVATE__YOUR_FILES_GITIGNORED/`.
  `chain doctor` and the full suite (119 tests, verified from both the true root and
  ENGINE) confirm clean.
- Batch 4 (docs/UX polish, no structural change): swept every doc for the "Workspace"
  concept Batch 2 retired — `architecture.md` had two survivors (design principle 2's
  worked example, and "all learned state lives in chain_home," both now wrong since
  generated output moved out), plus stale comments in `editorial_library.py` and
  `produce.py`, plus one in `examples/sample-bundle-packet.md`. `docs/intake.md` said
  "run the CLI from the repo root" (now wrong — it's ENGINE__PUBLIC_GIT_TRACKED/) and
  listed drafts as living in `chain_home` (they don't anymore); repeated the same
  stale "forbidden from writing inside the repo" privacy claim `chain-intake.md`/`.toml`
  already had fixed in Batch 3.
  README.md had no explanation of the three-root model anywhere — a new user would
  hit `PRIVATE__YOUR_FILES_GITIGNORED` and `ENGINE__PUBLIC_GIT_TRACKED` in the
  Quickstart with zero context. Added a "Folders" section (before Quickstart, so the
  names are explained before they appear in a command) and corrected "Core concepts"
  — a Draft's CSV row is metadata; the actual text lives in the review root, not
  `chain_home`.
  Explicitly deferred, per direction: "run chain commands from
  ENGINE__PUBLIC_GIT_TRACKED/" stays exactly as Batch 3 left it. This is real technical
  debt, not a docs gap — long-term, a user should be able to run CHAIN from the repo
  root without knowing where the engine physically lives. Not solved this pass;
  tracked as a running ENGINE-internal observation, see below.
  Full suite (119 tests) still green; no code paths changed, comments/docs only.
- Batch 5: resolved that debt with a root-level launcher rather than an install step
  or global PYTHONPATH change. New tracked, executable `./chain` (bash) at the repo
  root: resolves its own location to find `ENGINE__PUBLIC_GIT_TRACKED/` regardless of
  the caller's CWD, prefers `.venv/bin/python3` over PATH `python3` when present,
  verifies PyYAML is importable before doing anything else (clear actionable message
  + exit 1 if not — install pyyaml or create `.venv`), then `cd`s into the engine dir
  and `exec`s `python3 -m chain.<module> "$@"` — no CLI logic duplicated here, each
  `chain.*` module still owns its own arguments (including `--help`), and `exec`
  forwards the exact exit code rather than wrapping it. `./chain` with no args or an
  unrecognized module name lists real runnable modules, discovered by grepping for
  `__main__` blocks in `chain/*.py` rather than a hardcoded list that could drift.
  Verified for real, not just read: `./chain doctor`, `./chain intake --help`,
  argument forwarding on a real intake run (`./chain intake
  examples/demo.config.yaml --json` — confirmed real file counts, not just echoed
  config), exit-code forwarding on both success and argparse failure (2), and two
  failure-path simulations with an isolated PATH (no python3 anywhere → clear message
  + exit 1; python3 present but PyYAML unimportable → clear message + exit 1). One
  design note worth keeping in mind for anyone touching this script later: relative
  path *arguments* the user passes to `./chain <module>` (e.g. a config path) are
  resolved relative to `ENGINE__PUBLIC_GIT_TRACKED/`, where the command actually
  executes — not the repo root the user is standing in. Caught this myself
  mid-implementation by testing with the wrong-context path and silently getting
  the example config's placeholder defaults back instead of real data; the fix was
  documenting it clearly (the script's own usage text says so), not trying to
  rewrite path arguments, which would have meant guessing which arguments are paths.
  Updated every place that told a user/agent to `cd ENGINE__PUBLIC_GIT_TRACKED/` first
  (README Quickstart, both `chain-intake` agent files, `chain.config.example.yaml`,
  `docs/intake.md`, `examples/intake-personas/README.md`) to use `./chain <module>`
  from the repo root instead, and updated the two runtime messages
  (`changelog_sync.py`, `doctor.py`) that suggested the old `python3 -m chain.X` form.
  README also gained a one-line pointer to `./chain` ahead of the Quickstart block.
  Did not touch `canon/`, `docs/`, or `examples/` organization — that's still open,
  see the running observations below. Full suite (119 tests) green.
- Batch 6: fixed the one real gap Batch 5 left — path *arguments* to `./chain
  <module>` resolved from `ENGINE__PUBLIC_GIT_TRACKED/` (documented, but still an
  implementation detail leaking through, since the whole point of the launcher was
  to hide it). Direction was explicit: don't just document it, fix it, and don't
  guess which arguments are paths. Removed the `cd "$ENGINE_DIR"` from `./chain`
  entirely — the process's working directory now stays at the repo root for the
  whole invocation. `chain` is made importable by exposing
  `ENGINE__PUBLIC_GIT_TRACKED/` to that one child process via a `PYTHONPATH` prefix
  on the `exec` line itself (`PYTHONPATH="$ENGINE_DIR:$PYTHONPATH" exec "$PYTHON" -m
  "chain.$MODULE" "$@"`) — scoped to that single command, never exported into the
  user's shell, matching "expose ENGINE only to that child process" rather than a
  global environment change.
  This flips which direction the demo/persona example configs' internal relative
  paths need to point: since CWD is the repo root again (not ENGINE), `chain_home:
  ../.chain/...` reverted to `./.chain/...` (`.chain/` lives at the true root, one
  level closer now), and `sources:`/`voice_spec` paths that were bare
  `./examples/...` (correct only when CWD was ENGINE) needed the
  `ENGINE__PUBLIC_GIT_TRACKED/` prefix put back — across `demo.config.yaml`,
  `demo-studio.config.yaml`, and all three `intake-personas/*.config.yaml`. Verified
  each individually via a real `./chain intake` run, not just inspection — file
  counts, not just non-empty paths.
  `test_intake.py`'s `_resolve_relative()` helper (added in Batch 5 specifically to
  make persona tests CWD-independent) needed the same flip: it resolved relative
  config paths against `REPO` (the test file's own directory, i.e. `ENGINE`) — now
  resolves against a new `TOP_ROOT = REPO.parent`, matching the true-root-relative
  convention the configs use again. `CliTests`' two raw-text substitution targets in
  the same file flipped the same way (`../.chain/intake-p1` → `./.chain/intake-p1`;
  `./examples/` → `./ENGINE__PUBLIC_GIT_TRACKED/examples/`).
  Updated every doc path example accordingly: README Quickstart, both `chain-intake`
  agent files (including two `canon/...` mentions that were sibling-relative-correct
  under the old model but needed the prefix now), `docs/intake.md` (a stale
  "resolves against ENGINE__PUBLIC_GIT_TRACKED/" line plus two more `canon/`
  mentions), and `examples/intake-personas/README.md`. Left markdown *hyperlinks*
  (`[text](../canon/foo.md)`, resolved by the renderer relative to the file, not by
  the launcher) and `docs/privacy.md`'s categorical table entries alone — genuinely
  unaffected by this change, not an inconsistency.
  Verified for real: `./chain doctor`; the exact repo-root-relative path from the
  task (`./chain intake ENGINE__PUBLIC_GIT_TRACKED/examples/demo.config.yaml
  --json`); a relative *private* config path
  (`PRIVATE__YOUR_FILES_GITIGNORED/chain.config.local.yaml`, resolving all of
  Jessica's real sources); `--help` and exit-code forwarding (0 / 2); the two
  environment-not-ready failure simulations from Batch 5, re-run against the new
  script. Full suite (119 tests) green from both the repo root and
  `ENGINE__PUBLIC_GIT_TRACKED/`.
  This closes the filesystem architecture migration — ENGINE / PRIVATE /
  READY-TO-REVIEW all exist, are documented consistently, and are usable from the
  repo root with no implementation detail leaking through. `canon/`, `docs/`,
  `examples/` internal reorganization remains open (running observations, unchanged)
  but is explicitly a separate, later pass — not blocking.
- Batch 7: repointed `chain.config.local.yaml` to Documents/Writing's reorganized
  structure (`projects-and-sites/published/drafts/guidelines/analysis-and-tools`,
  see Writing's own git history for that change). The old single `website` source
  dissolved into three per-project entries — kept as separate entries rather than
  one blanket `projects-and-sites` source, since a blanket entry's path would be a
  parent of two other reference sources' paths and double-ingest their content
  (the ingestion ledger dedupes per (source, path), not globally by file, so two
  source names covering the same file is a real double-count, not just redundant).
  `drafts` + `draft-ideas` merged into one `drafts` source (both role tags
  preserved) matching Writing's own consolidation.
  Simplified `PRIVATE__YOUR_FILES_GITIGNORED/`: the old `canon/` (4 file symlinks)
  and 9 Writing-related entries under `sources/` collapsed into one `writing/`
  folder with 4 directory-level symlinks (`guidelines`, `projects-and-sites`,
  `published`, `drafts`) — purely a visibility simplification, since CHAIN's code
  never reads through `PRIVATE__YOUR_FILES_GITIGNORED/`, only through
  `chain.config.local.yaml`'s real paths. `sources/application` and
  `sources/applications-2026` (not Writing paths) kept as-is. Verified with a real
  `./chain intake --json` run — every source resolves with a sensible file count,
  no zero-file source, no evidence of the double-ingestion this design avoids.
  `chain doctor` and the full suite (119 tests) confirm clean.

## Pre-2026-07-13 — Everything before the changelog existed

- CHAIN shipped the privacy firewall, config pattern, editorial library, adaptive
  intake, idempotent source intake + idea harvesting, the domain-agnostic Discover
  synthesis, and the production spine (Brief → Draft → Evaluate → bounded Finalize)
  before this changelog began. See `docs/architecture.md` and the repo's `README.md`
  Status section for that history.

## Earlier — Origins

- CHAIN began as an editorial-automation idea to turn a person's own writing and
  project notes into new public work without becoming another content mill.
