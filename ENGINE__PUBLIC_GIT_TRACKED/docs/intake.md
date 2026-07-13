# CHAIN — Adaptive Intake

CHAIN onboards users at **any** level of editorial maturity. The core principle:

> CHAIN never requires users to have already done the work that CHAIN exists to help
> them do.

Intake is not a questionnaire and not a migration. It inspects what already exists,
classifies every editorial input as **exists / partial / missing**, and then does the
smallest useful thing for each: validate in place, improve, or create a first version
collaboratively.

## Two halves

| Half | What it does | Cost |
|---|---|---|
| **Deterministic core** — `./chain intake` | inspects sources + assets, classifies each, computes your maturity level, generates the plan (blockers first), writes the durable manifest, prints the one progress summary | zero tokens |
| **Collaborative layer** — the `chain-intake` agent | locates scattered material, proposes source maps, interviews, runs writing exercises, distills guidance from raw material, creates first versions from `ENGINE__PUBLIC_GIT_TRACKED/canon/*.template.md` | model-backed |

The agent always runs the core first and works from its report; the core is
idempotent, so every finished asset is recorded and never re-asked.

## The maturity model (computed, never asked)

| Level | Looks like | Intake behavior |
|---|---|---|
| **1 — already organized** | corpus + voice guidance (+ maybe strategy) exist | map in place, validate, surface only real gaps, get out of the way |
| **2 — raw material, no system** | useful material scattered across folders/exports (FAQs, reviews, posts, notes, applications) | classify sources, propose a durable map, **distill** missing guidance from the material itself |
| **3 — starting from almost nothing** | rough notes, expertise, goals — little or no public writing | guided interview + short writing exercises create a seed corpus (role `samples`) and first-version voice + positioning. Never "come back later." |

A Level-3 session ends at Level 2 by design: the seed corpus is *usable but thin*,
and only a real body of representative writing (8+ pieces, grown over time) reaches
Level 1. Thin-but-usable never blocks — it shows up as "worth strengthening", not as
a blocker.

## Editorial inputs covered

Required (block writing quality): **source map · representative writing · voice &
style guidance · positioning/reputation signals**. Recommended: themes ·
anti-patterns · audience & outcomes. Optional (offered once, never pushed): drafts ·
principles · story bank · exemplar index · feedback ledger · channel guidance.

Every input supports the three states. Existing files are referenced **where they
live** (`--set-path asset=/their/real/path`) — intake never relocates anything. It
may recommend a layout to someone starting from scratch; it never requires one.

## Commands

Run from the repo root — `./chain` finds the engine for you:

```bash
./chain intake                      # inspect, plan, update manifest, summary
./chain intake my.config.yaml --json
./chain intake --set-path themes=~/notes/what-i-write-about.md
./chain intake --mark voice_spec=created   # user-provided | improved | created
./chain intake --skip story_bank           # anything except required assets
./chain intake --reviewed voice_spec       # stamp last_reviewed
```

`--set-path` is only needed when a file lives somewhere non-default — assets created
at their default `chain_home` location are detected automatically on the next run.
Relative paths in a config resolve against the repo root (`./chain` keeps your working
directory there) — use absolute paths in configs you keep elsewhere to avoid depending
on that.
`--skip` silences recommended as well as optional assets (a deliberate "not for me"
is respected); only the four required assets can't be skipped.

`./chain doctor` warns when no manifest exists yet. The collaborative flow: open the
repo in Claude Code and ask for intake — the `chain-intake` agent handles the rest,
one asset at a time, per `ENGINE__PUBLIC_GIT_TRACKED/canon/intake-interview-guide.md`.

## The manifest

`chain_home/state/intake-manifest.json` — the durable record. Locations and statuses
only, **never source content**:

```json
{
  "version": 1,
  "created": "…", "updated": "…",
  "maturity_level": 2,
  "sources": [{"name": "…", "path": "…", "roles": ["…"], "enabled": true, "files": 12}],
  "assets": {
    "voice_spec": {
      "label": "Voice & style guidance", "tier": "required",
      "status": "exists | partial | missing",
      "path": "/where/it/lives",
      "detail": "why it classified that way",
      "provenance": "user-provided | improved | created",
      "last_reviewed": "…", "skipped": false, "notes": "…"
    }
  },
  "blockers": ["…required assets not yet at exists…"]
}
```

Statuses are recomputed from disk on every run; human-set fields (provenance, paths,
skips, review dates, notes) are preserved across runs. An asset with `status:
"exists"` and empty `provenance` means auto-detected — the deterministic core found
it without anyone vouching for it; `user-provided` means a human confirmed it.

## Privacy (church and state)

The repo ships mechanism: intake logic, templates, prompts, docs, synthetic personas,
tests. The user's voice spec, strategy, corpus, feedback, source paths, and manifest
live in `chain_home` or wherever the user already keeps them; drafts live in the
review root — external or gitignored, always. The intake agent is forbidden from
writing user content anywhere git-tracked. See [privacy.md](privacy.md).

## Lessons from the first real onboarding (reference case, de-identified)

Intake's shape comes from a real Level-1/Level-2 hybrid onboarding: an author with
years of published work and useful material scattered across several private
locations, but no unified system. What generalized:

- **Locating beats recreating.** Most "missing" assets existed in fragments — an old
  style blurb, a strategy note, red-flag research. Intake asks before it creates.
- **Preserve provenance.** Raw inputs (an old guide, an external voice analysis)
  were kept as `source-docs/` beside the distilled specs. Distillations supersede
  sources at runtime; sources make the distillation auditable and improvable.
- **Distill from evidence, not self-description.** The voice spec came from the
  corpus plus accumulated feedback, then a keep/wrong/more-like-this review — people
  describe their voice aspirationally; their reactions are reliable.
- **Signals ≠ themes.** "What readers should come to believe" (positioning) kept
  getting tangled with "what the writing is about" (themes). Separating them is a
  deliberate intake step.
- **A feedback ledger changes the game.** Introduced empty, it gives every later
  reaction a durable home that outranks the specs — the system improves from use.
- **Wire config last.** Only after assets stabilized were `voice_spec` /
  `positioning_pillars` pointed at them; doctor going fully green is the done signal.
- **Judgment vs. determinism.** Classifying files, counting corpus, validating
  pillar tables, tracking status: deterministic. Choosing roles for ambiguous
  sources, distilling voice, naming pillars: judgment, always with user review.
- Author-specific choices (which folders, which register splits, publish channels)
  stayed OUT of the mechanism — they're config and canon, not code.

## Non-goals for V1

- No PDF/DOCX/Pages extraction and no cloud connectors (Google Docs, Notes, email) —
  users export to local text; intake maps the export.
- No automatic re-interviewing on file changes — `last_reviewed` supports manual
  revisits.
- No multi-user or team intake; one author per config.
- No auto-generated writing beyond the seed exercises the user writes themselves.
- Assisted/deep *source-map proposal* (`intake.mode`) remains the agent's job at the
  user's request — no background token spend.
