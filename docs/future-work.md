# CHAIN — Future Work

What is intentionally **not** in V1. Recorded so the boundary is visible and nothing
here gets quietly built early. V1 scope is the [architecture](architecture.md).

## In V1 (for the record — do NOT defer these)

- Short-form **and** long-form support
- Channel-aware writing rules (rule packs; LinkedIn is one)
- Directed user inputs (premise, notes, draft, file, URL, backlog item, expand, companion, custom)
- Long-form + companion-post bundles, with the evaluator's bundle mode
- Ideas-backlog aggregation and published-piece indexing
- Relationships among ideas and pieces (derived + linked)
- Generic marker-based idea harvesting from any source (job-application folders are one example)
- Basic backlog hygiene (dedup, link, mark-produced, preserve-rejected, evergreen vs
  time-sensitive, resurface-on-new-material, honor user interest)
- The five-output autonomous run preset

## Known limitations (V1)

- **Bundle-level revision is not wired.** The evaluator's bundle mode can *identify*
  pair-level problems (redundancy, incoherence, weak angle), but a bundle-level finding
  does **not** yet trigger a bounded revision of one of the two drafts — it is reported in
  the bundle packet only. This is acceptable for now: the first real-world V1 test
  generates five **independent short-form** drafts, which never enter bundle mode. Bundle
  revision (feed the bundle finding back into one draft's single-draft spine, once,
  preservation-checked) should be completed **before bundles are treated as fully
  production-ready.**

## V2

- **Missing-evidence detector** — identify important capabilities absent from the
  public-writing corpus.
- **Engagement ingestion and performance analysis.** Assume metrics arrive at
  multiple points in time and need a **separate time-stamped history file** keyed by
  `piece_id` (e.g. `analytics-history.csv`), never a single cell in `pieces.csv`.
- Recruiter / hiring-manager response logging.
- Research layer.
- Sophisticated topic-coverage / repetition analysis (V1 has only a light overuse guard).
- Optional human checkpoint after ideation (V1 runs Discover→Finalize fully autonomously).
- Additional source connectors.
- More structured human-feedback classification.

## V3

- Automated analytics retrieval.
- Source lineage for professional claims.
- Audience-segment analysis.
- Advanced cross-piece narrative planning.
- Automated publishing or scheduling (V1 and V2 never publish — that stays the human's move).
- More advanced experimentation around levels of human intervention.
- Advanced per-register personalization.

## Design notes to honor when these are built

- **Engagement never becomes the primary target.** Positioning Impact stays primary;
  analytics informs, it does not optimize the writer toward past top performers.
- **The prepares-not-publishes guardrail is permanent.** No CHAIN version posts on
  your behalf.
- **The public/private firewall is permanent.** New features add mechanism to the
  repo and data to chain_home — never personal data to git.
