# CHAIN — agent instructions

See `README.md` and `docs/architecture.md` for what this repo is and how it works.
This file holds the one standing rule every coding agent working here must follow.

## Repo changelog (required — applies to every coding agent)

`docs/changelog.md` is this repo's own project history — not editorial output, and
separate from anything CHAIN produces for a user. **Any coding agent working in this
repo — Claude Code, Codex, or otherwise — must add a rough dated entry to
`docs/changelog.md` in the same turn as any meaningful change, or explicitly say in
the reply that no entry is warranted and why. This is part of finishing the work, not
an optional follow-up or something the user needs to request.**

- **Entry required:** new or changed engine behavior (intake, discover, produce,
  bundle, lint, doctor), config or schema changes, privacy/firewall-relevant changes
  (`path_safety.py`, the `chain_home` boundary), architecture or design-principle
  changes, documentation that changes how the system is understood, and explorations
  that reached a real conclusion even when nothing shipped.
- **No entry needed:** typo fixes, formatting/comment-only edits, tiny polish, and
  other purely mechanical maintenance.
- Capture what changed and, when you know it, why — the user problem, confusion, or
  test result that prompted it, a privacy/trust concern, a simplification or
  complexity-removal decision, or a case where real use contradicted the plan. Rough
  and unpolished is fine; keep it dated and terse. Don't wait for synthesis to clean
  it up before capturing it.
- If you're committing the related work, commit the changelog entry in the same
  commit.
- **Synthesis** (consolidating rough entries into readable threads and refreshing
  `docs/architecture.md`) is a separate, occasional pass that only runs when the user
  asks for it — see `chain/changelog_sync.py`'s module docstring. Don't run it
  automatically as part of ordinary work, and don't wait for it before capturing a
  rough entry.
