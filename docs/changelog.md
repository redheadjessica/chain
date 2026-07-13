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
  pattern here, not just an implementation shortcut. Deliberately did NOT touch
  `chain_home/workspace` (the actual review-output relocation is a separate,
  not-yet-decided batch — see the open question raised in chat) or move any public
  engine files (`chain/`, `canon/`, `docs/`, `examples/`, `tests/` still at repo
  root).

## Pre-2026-07-13 — Everything before the changelog existed

- CHAIN shipped the privacy firewall, config pattern, editorial library, adaptive
  intake, idempotent source intake + idea harvesting, the domain-agnostic Discover
  synthesis, and the production spine (Brief → Draft → Evaluate → bounded Finalize)
  before this changelog began. See `docs/architecture.md` and the repo's `README.md`
  Status section for that history.

## Earlier — Origins

- CHAIN began as an editorial-automation idea to turn a person's own writing and
  project notes into new public work without becoming another content mill.
