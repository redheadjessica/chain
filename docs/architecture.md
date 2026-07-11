# CHAIN — Architecture

**CHAIN — Contextual Human-AI Narrative System.** An editorial engine that
discovers or develops *ideas* from your own writing and takes them through a shared
production spine into finished *pieces* — a LinkedIn post, a Medium article, a
companion post, a website essay. It **prepares**; you **publish**. If writing every
piece by hand chains you to your desk, CHAIN helps you get out.

Channel-neutral by design; the first proof of concept targets LinkedIn, but nothing
in the engine is LinkedIn-shaped.

---

## Design principles

These override feature ambitions. When two designs are equally capable, the one that
honors these wins.

1. **Adapt to the user's world.** CHAIN never requires anyone to move their writing,
   job applications, projects, website, or resumes into a CHAIN-specific folder
   hierarchy. Intake *maps existing locations* into CHAIN's model, the way a good
   résumé tool reads your existing folders in place. A recommended layout for
   brand-new users is only ever an example, never a requirement.
2. **Single source of truth.** Every piece of information has one canonical home.
   CHAIN indexes, normalizes, and *references* existing material instead of copying
   it into new permanent locations. The only exception is the **Workspace**, which
   holds intentionally disposable generated drafts.
3. **Minimize cognitive overhead.** Prefer fewer persistent concepts, fewer
   directories, fewer configuration surfaces, fewer review queues, fewer manual
   approval steps, fewer places to remember where something lives. Every new durable
   file, stage, queue, index, or config surface must remove more complexity than it
   adds. The goal is *the smallest set of durable concepts that supports a powerful
   editorial workflow* — not maximum flexibility.

---

## Where things live (two ideas, not three)

There is no "Profile." CHAIN distinguishes only:

- **Your world (referenced in place, read-only).** Your writing, applications,
  website, project repos — and your canon inputs (voice spec, positioning pillars).
  CHAIN reads these where they already are. Nothing is relocated or copied durably.
- **CHAIN's home (`chain_home`, one writable root, default `~/.chain`, relocatable).**
  The only place CHAIN owns. Holds the state CHAIN itself authors — which does not
  pre-exist in your world — plus the disposable Workspace:

  ```
  chain_home/                 (default ~/.chain; may live anywhere outside the repo)
    library/
      ideas.csv               # the persistent ideas
      pieces.csv              # every piece of writing (draft -> published)
    feedback.md               # confirmed learning (created on first lesson)
    stories.md                # story index (created on first harvest; pointers, not copies)
    workspace/                # disposable: generated briefs, drafts, packets
  ```

**Why this is the minimum.** Ideas, the pieces index, and learned feedback are things
CHAIN writes and must persist; they have no home in your existing folders, so they
need exactly one place CHAIN owns. Everything else you already have stays where it is
and is referenced. That's the fewest durable concepts the workflow can run on.

Configuration is correspondingly small:

```yaml
chain_home: ~/.chain                 # the one writable root (workspace lives inside)
voice_spec: ~/.chain/voice-spec.md   # a reference; point it at a file you already have
positioning_pillars: ~/.chain/positioning-pillars.md
sources: [ ... ]                     # your existing folders, mapped in place
```

The repository ships the mechanism and generic templates — never your data. The
runtime firewall refuses to run if `chain_home` resolves inside the repo without being
gitignored. See [privacy.md](privacy.md).

---

## Intake: adapt to the corpus *and* the budget

CHAIN adapts to where your material lives **and** to how much model-assisted setup you
want to pay for. Intake is three **levels of assistance around one source-mapping
model** — not three systems:

| Level | What it does | Model cost |
|---|---|---|
| **Manual mapping** | You state paths, `type`, include/exclude, filenames, markers, and what each source contains. Deterministic indexing. | ~none |
| **Assisted mapping** *(recommended default)* | CHAIN samples a bounded number of files, proposes a source config, and you confirm or correct it. Sample size and model are configurable for cost. | bounded, tunable |
| **Deep discovery** *(opt-in)* | CHAIN inspects a broader, messier corpus and proposes a full mapping. Clearly labeled token-intensive. | higher |

The cost model is explicit: **organization and explicit mapping reduce tokens;
model-assisted discovery trades tokens for less manual setup.** A tidy corpus can be
mapped manually with almost no inference; a messy one can opt into deeper inspection.

## Durable source mappings and the ingestion ledger

Model-assisted intake exists to produce **durable configuration, not per-run
reasoning.** Once CHAIN knows a folder holds job applications, a heading marks writing
ideas, another folder holds published posts, and a file is the voice spec, that mapping
is saved (it *is* the `sources:` config) and reused. CHAIN never re-asks a model to
rediscover structure on a normal run; you can remap a source when you want to.

Idempotency comes from an **ingestion ledger** in `chain_home/state/` — a deterministic
record keyed by `(source, path)` with each file's content hash, metadata, and the ideas
it produced. Every run:

- inspects **only new or changed files** (hash mismatch), skipping unchanged ones with
  zero model cost;
- uses deterministic include/exclude rules;
- never re-ingests an unchanged source, so **unchanged sources produce no duplicate
  ideas**;
- prevents **exact** duplicate ideas automatically and merely **flags near-duplicates**
  without blocking intake.

The ledger and cache store references, hashes, extracted metadata, narrowly necessary
excerpts, and normalized indexes — **never full copies of your files.** The cache is
not a second archive of your corpus. (Single source of truth; the Workspace remains the
only disposable-copy exception.)

---

## The core objects: Ideas and Pieces

**User-facing language (use these everywhere — docs, commands, packets):**
- **Idea** — a possible premise or direction.
- **Draft** — an unpublished expression of an idea.
- **Published writing** — the final public work, wherever its canonical text or URL
  already lives.

"Writing" always means *published* work; unfinished work is a **Draft**, never
"writing." Internally a **Piece** is the row that carries a status (`draft → final →
published`, or `parked`); "Drafts" and "Published writing" are status views of Pieces,
never separate stores. A published post is the same Piece its draft was. CHAIN does not
copy published text into itself when the canonical text already lives in your library —
it references it there.

**Data model** — two flat CSVs joined by stable IDs, human-editable in a spreadsheet,
owned by [`chain/editorial_library.py`](../chain/editorial_library.py):

- `ideas.csv` — the persistent idea. **No `piece_ids` column**: an idea's pieces are
  *derived* by filtering `pieces.csv` on `idea_id`, so the relationship is stored once
  and can't fall out of sync.
- `pieces.csv` — one row per piece; carries `idea_id` (its origin), a `status`, and
  `parent_piece_id` / `related_piece_ids` for companion / expansion / follow-up links.
  `url` / `final_text_path` *point at* where the piece lives; the index is a reference,
  not a second canonical archive (single source of truth).
- Multi-value cells (`related_idea_ids`, `related_piece_ids`) use `|`, never a comma.
- **No analytics column.** Engagement is V2 and will live in a separate, time-stamped
  history file — never one overloaded cell. See [future-work.md](future-work.md).

**Same idea vs new idea (brief-development rule):** when a short post becomes a
long-form article, or an article gains a companion, those Pieces **share one
`idea_id`** — they're new expressions of one idea. A **new** Idea is created only when
the work introduces a materially different *premise*. Brief development makes this call
explicitly and records the reason when it forks a new idea.

**Lightweight manual entry:** adding an idea by hand needs only a `working_title` and a
`premise`. `groom()` assigns the ID and fills the rest — never a large intake form.

---

## Two entry modes, one spine

```
  Discover mode ─┐                     ┌──────────────────┐
  (scan your      │                    │ Draft → Evaluate │
   world,         ├─► IDEA ─► BRIEF ─► │   (bounded 1×)   │ ─► PIECE(s) + packet
   synthesize,    │        (output     └──────────────────┘
   seed ideas)    │         spec)              │
  Directed mode ─┘                     bundle? → Evaluate in bundle mode
  (user input enters
   at the brief stage,
   skipping the sweep)
```

**Discover mode** (autonomous): connectors normalize your sources → a multi-lens sweep
proposes idea seeds (recurring-answer, convergent-demand, fresh-lesson, old-meets-now,
latent-POV, overuse-guard) → seeds merge into the backlog under the hygiene rules →
selection picks N by positioning value, freshness, timeliness, and **your stated
interest** → selected ideas develop into briefs.

**Directed mode** (you provide input — a premise, notes, a partial draft, an
application answer, a file, a URL, a backlog idea, a short post to expand, an article
needing a companion, or a custom request): the input is normalized into an idea (new or
matched) and **enters at the brief stage**. It does not run the sweep.

Both converge on **Brief → Draft → Evaluate → Finalize**.

---

## The brief is the output specification

The brief is the pivot that lets one writer/evaluator serve every channel:

- `format`: short_post · long_post · article · companion_post · custom
- `channel`: linkedin · medium · substack · website · neutral
- `target_length`, `audience`
- `relationship`: standalone, or expands / condenses / promotes / follows-up another piece
- `link_strategy`, `call_to_action`
- `primary_pillar` (+ optional `secondary_pillar`)

The writer and evaluator retrieve the matching **channel** and **format** rule packs and
exemplars at runtime. Channels and formats are *data files*, so adding one is a file,
not a refactor.

---

## Writer / Evaluator / Lint — one of each

- **`chain-writer`** — drafts one piece from a brief + canon references + cited source
  excerpts; surgeon in revise mode (touches only cited lines); autonomous (defers
  uncertainty to the packet); lint-gated.
- **`chain-evaluator`** (never rewrites) — the honest broker. Scores **Positioning
  Impact** (primary) and **Voice**; runs self-pushback and a gold/negative exemplar
  comparison; owns the packet's candid verdict. Runs per piece, then **once in bundle
  mode** for an article+companion pair. Bundle coherence is a *mode of this same
  evaluator*, not another agent.
- **`lint_draft.py`** — **mechanical compliance only**: banned phrases/patterns,
  punctuation, length ranges, paragraph structure, external-link rules, hashtag counts,
  repeated punctuation, required-section presence, format-specific mechanics. It never
  judges hook strength, originality, emotional impact, or quality — **those are the
  evaluator's job.** Channel/format rule packs are selected by the brief; LinkedIn is
  one pack.

**Bounded revision:** exactly one Evaluate → (conditional) Revise cycle, then ship with
remaining concerns as flags.

---

## Positioning Impact is the primary target

Not engagement. CHAIN evaluates whether a piece strengthens the professional impression
the writing is meant to create, against the configured pillars (shipped example set,
customizable via the `positioning_pillars` reference):

1. Sharp product thinker  2. Current and technically fluent  3. Experienced and
operating at full strength  4. Distinctive and engaging  5. Warm, perceptive, and human
6. High-agency builder

Each piece has one primary intended impression and, optionally, one secondary. Resonance
is advisory only in V1 and never drives scoring.

---

## Bundles: long-form + companion, first class

A run can emit `{article, companion_post}` — two Pieces sharing one `idea_id`, linked
`companion-of`. The companion is **not a summary**; its brief carries a `companion_angle`
(one observation · the origin story · the central tension · one example · why it was
written · a related distinct angle). The evaluator judges each piece independently, then
in **bundle mode**: coherence, whether the companion drives interest in the article,
whether it stands alone, whether the two are unnecessarily repetitive, channel fit.
Bounded: two members in V1.

---

## The packet

Per piece: the paste-ready text, a scorecard (Positioning Impact + Voice, must-fixes
resolved), open questions, and the **editorial confidence section** authored by the
evaluator (Why CHAIN chose this · What this communicates about you · Why you have
standing to say it · Reasonable publication risk · Editorial verdict). Candid and
evidence-based; never instructed to persuade you a piece is good. A bundle adds a pair
section. Full anatomy in [packet.md](packet.md).

---

## Runs are configurable

A run spec sets: number of pieces, allowed formats, default channel, whether long-form
is allowed, whether long-form auto-receives a companion, and whether ideas come from
Discover, the backlog, a user input, or a mix. The **first proof-of-concept preset**
produces **five short/medium LinkedIn-ready pieces**
([examples/runs/five-linkedin.yaml](../examples/runs/five-linkedin.yaml)). The engine
also supports (but the first run doesn't require) a directed premise, one article, an
article+companion bundle, and expanding an existing piece.

---

## One backlog (V1, deliberately un-clever)

There is **one main ideas backlog** (`ideas.csv`). Everything flows into it: your
manually entered ideas, writing ideas harvested from job applications, unfinished
drafts, CHAIN-generated ideas, and published pieces worth expanding or following up.
**No per-source review queues.** Harvested ideas enter automatically with status
`proposed`; you rank, annotate, park, or reject them in one place.

- **Reject** preserves the reason and drops the idea from the normal active view
  (`active_ideas()` hides `rejected`/`parked`). A later view/tab may expose rejected
  ideas; you are never asked to review the same idea repeatedly.
- **Exact duplicates are prevented automatically; near-duplicates are flagged, not
  blocked.** Intake never stalls on a merge approval.
- `chain groom` does only hygiene: link related ideas, mark ideas produced once a piece
  exists, distinguish evergreen vs time-sensitive (auto-park expired), and weigh your
  stated interest alongside CHAIN's assessment.

---

## The human-confirmed learning loop (V1: minimal)

Ground truth is **your confirmed final published text.** You review packets, edit, and
post manually — CHAIN never publishes. Learning stays grounded and low-overhead:

- **CHAIN may retain automatically**, per piece: the generated draft, your final edited
  version, the **diff** between them, and any explicit explanation you give. These are
  facts about one piece, kept as references (not copies of published text — that lives
  in your library).
- **It does NOT auto-convert every edit into a universal voice rule or story-bank
  entry.** A context-specific edit may be accidental, tactical, or relevant only to that
  piece. Over-generalizing edits is exactly the failure this avoids.
- **Inferred reusable lessons** are surfaced as a **very lightweight confirmation inside
  the normal run report** (a one-line yes/no), never a separate standing review queue.
  The confirmed final text is ground truth; *generalized rules still require your
  confirmation.*

All learned state lives in `chain_home`, never in git. Engagement-driven learning is V2.

---

## Reused from the cover-letter system vs rebuilt

**Reused:** Draft → Evaluate → Finalize; writer/evaluator split with a non-rewriting
evaluator; deterministic lint gate + anti-smoothing preservation; one bounded revision;
church-and-state learning with the observed/inferred firewall; structured schemas;
autonomous mode; the review packet; gold/negative exemplar comparison + self-pushback;
prepares-not-publishes; single-source-of-truth canon and truth/standing discipline.

**Rebuilt / new:** the Idea/Piece model + editorial library; Discover and Directed
modes; the map-in-place config + connector intake; the two-ideas location model
(no Profile); channel/format rule packs (LinkedIn as one pack); Positioning Impact as
the primary axis; the expanded packet; bundles + the evaluator's bundle mode;
configurable runs; job-application idea harvesting.

See [future-work.md](future-work.md) for what is intentionally deferred.
