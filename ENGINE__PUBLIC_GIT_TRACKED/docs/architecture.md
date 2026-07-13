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
   it into new permanent locations. The one exception is generated output (drafts,
   packets) — CHAIN originates it rather than referencing something that already
   exists, so its canonical home is `__READY_TO_REVIEW__PRIVATE_GITIGNORED/`.
3. **Minimize cognitive overhead.** Prefer fewer persistent concepts, fewer
   directories, fewer configuration surfaces, fewer review queues, fewer manual
   approval steps, fewer places to remember where something lives. Every new durable
   file, stage, queue, index, or config surface must remove more complexity than it
   adds. The goal is *the smallest set of durable concepts that supports a powerful
   editorial workflow* — not maximum flexibility.
4. **Visible structure over hidden convenience.** Where a person needs to find or
   inspect something — their own source material, canon references, or CHAIN's
   generated output — prefer a clearly named, visible location over one reachable
   only through configuration or an internal working directory. When CHAIN depends on
   canonical content that lives elsewhere, expose it through a clearly named symlink
   rather than duplicating it or hiding the dependency behind config alone, as long as
   a single source of truth is preserved. Human-facing artifacts — anything a person
   is expected to open, edit, or review — belong in a canonical, visible location;
   hidden directories (`.chain/cache`, `.chain/state`, and the like) are for machine
   state only: caches, indexes, manifests, logs. Never for something a person is
   expected to browse. When choosing between preserving an existing implementation
   and making the system easier for a new person to understand, prefer the latter
   unless the migration cost is genuinely significant. (Learned from applying this
   same principle to JAIL, CHAIN's sibling engine.)

---

## Where things live

There is no "Profile." CHAIN distinguishes three locations, matched to who each is
for:

- **Your world (referenced in place, read-only).** Your writing, applications,
  website, project repos — and your canon inputs (voice spec, positioning pillars).
  CHAIN reads these where they already are. Nothing is relocated or copied durably.
- **`chain_home` (default `~/.chain`, relocatable) — machine state plus the durable
  library.** Holds the ingestion cache and ledger (pure machine state, never meant to
  be browsed) and the state CHAIN itself authors that must persist — the library and
  any confirmed learning:

  ```
  chain_home/                 (default ~/.chain; may live anywhere outside the repo)
    cache/                     # search/embedding cache — machine state, hidden
    state/                     # ingestion ledger, intake manifest, selection log — machine state, hidden
    library/
      ideas.csv                # the persistent ideas
      pieces.csv                # every piece of writing (draft -> published)
    feedback.md                # confirmed learning (created on first lesson)
    stories.md                 # story index (created on first harvest; pointers, not copies)
  ```

  The library and any confirmed-learning files are durable and human-relevant even
  though CHAIN authors them — expose them with a visible symlink under
  `PRIVATE__YOUR_FILES_GITIGNORED/` rather than leaving them reachable only through
  `chain_home`. `cache/` and `state/` stay hidden.
- **`__READY_TO_REVIEW__PRIVATE_GITIGNORED/` (fixed, in-repo, gitignored) — generated
  output waiting on human review.** Every draft, packet, and finished-but-unpublished
  piece a run produces. This is the canonical location, not a pointer into
  `chain_home` or anywhere else — the same fixed, identically-named convention JAIL
  uses. Not separately configured.

**Why this is the minimum.** Ideas, the pieces index, learned feedback, and the
active drafts are things CHAIN writes and must persist; they have no home in your
existing folders, so they need places CHAIN owns or governs. Everything else you
already have stays where it is and is referenced. The review root is a placement
decision (visible vs. hidden), not a new durable concept layered on top.

Configuration is correspondingly small:

```yaml
chain_home: ~/.chain                 # machine state + library (generated output goes to
                                      # __READY_TO_REVIEW__PRIVATE_GITIGNORED/, fixed, not here)
voice_spec: ~/.chain/voice-spec.md   # a reference; point it at a file you already have
positioning_pillars: ~/.chain/positioning-pillars.md
sources: [ ... ]                     # your existing folders, mapped in place
```

The repository ships the mechanism and generic templates — never your data. The
runtime firewall refuses to run if `chain_home` or the review root resolves inside the
repo without being gitignored. See [privacy.md](privacy.md).

---

## Intake: adapt to the user's structure

CHAIN maps your existing folders in place. Setup is three **levels of assistance around
one source-mapping model** — not three systems — so you use as much or as little
model help as your corpus needs:

| Level | What it does |
|---|---|
| **Manual mapping** | You state paths, `type`, `roles`, include/exclude, and markers. Deterministic indexing. |
| **Assisted mapping** *(recommended default)* | CHAIN samples a few files, proposes a mapping, you confirm or correct it. Sample size and model are configurable. |
| **Deep discovery** *(opt-in)* | CHAIN inspects a broader, messier corpus and proposes a mapping. |

The bias is simple: prefer deterministic mapping when you already know your structure;
use model-assisted inspection when it meaningfully reduces manual effort. Users choose
their own model and manage their own usage — token budgeting is not a product concept
CHAIN foregrounds.

**Source roles.** Each source carries small, generic, domain-agnostic **role** hints —
`published`, `drafts`, `questions`, `feedback`, `reviews`, `research`, `projects`,
`offers`, `audience-needs`, `idea-source`, `reference`, `changes`, `custom` — that tell
Discover what kind of signal it may hold. A source may have several; unknown roles are
allowed. Roles are how CHAIN stays domain-agnostic: a product person's applications and
a studio's client questions are both role `questions`, read the same way. `type` is just
a reading-behavior label; no industry concept (résumés, recruiters, job descriptions) is
built into the core.

## Durable source mappings and the ingestion ledger

Model-assisted intake exists to produce **durable configuration, not per-run
reasoning.** Once a mapping is set — a folder's roles, a heading that marks an idea list,
which file is the voice spec — it *is* the `sources:` config and is reused. CHAIN never
re-asks a model to rediscover structure on a normal run; you can remap when you want to.

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
long-form piece, or a long-form piece gains a companion, those Pieces **share one
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

**Discover mode** (autonomous): connectors normalize your sources → the portable
`chain-discoverer` agent runs a sweep of eight **domain-agnostic lenses**
(`repeated-question`, `converging-signal`, `fresh-lesson`, `old-meets-now`, `latent-pov`,
`expansion-opportunity`, `translation-opportunity`, `coverage-guard` — see
[canon/discover-lenses.md](../canon/discover-lenses.md)) → it emits idea seeds with
evidence → a lightweight **deterministic** selection (dedup against the backlog +
diversify across lenses/pillars + cap) picks a few → selected ideas develop into briefs.
The seeds and their premises come from the LLM; selection does not re-score seed quality,
so it is not a quality ranking — only a dedup-and-spread.

**Directed mode** (you provide input — a premise, notes, a partial draft, an
application answer, a file, a URL, a backlog idea, a short-form piece to expand, a long-form piece
needing a companion, or a custom request): the input is normalized into an idea (new or
matched) and **enters at the brief stage**. It does not run the sweep.

Both converge on **Brief → Draft → Evaluate → Finalize**.

---

## The brief is the output specification

The brief is the pivot that lets one writer/evaluator serve every channel:

- `format`: short_form · long_form · companion_post · custom
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
  mode** for a long_form+companion pair. Bundle coherence is a *mode of this same
  evaluator*, not another agent.
- **`lint_draft.py`** — **mechanical compliance only**: banned phrases/patterns,
  punctuation, length ranges, paragraph structure, external-link rules, hashtag counts,
  repeated punctuation, required-section presence, format-specific mechanics. It never
  judges hook strength, originality, emotional impact, or quality — **those are the
  evaluator's job.** Channel/format rule packs are selected by the brief; LinkedIn is
  one pack.

**Bounded revision:** exactly one Evaluate → (conditional) Revise cycle. Findings carry
stable ids; the writer declares, per id, what it `addressed` and what it `declined`, and
the preservation lint uses that mapping so only the addressed passages may change. After a
revision, a single **re-evaluation reads** the revised draft (not another revision cycle)
so the packet's scores and verdict describe what you would actually publish.

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

A run can emit `{long_form, companion_post}` — two Pieces sharing one `idea_id`, linked
`companion-of`. The companion is **not a summary**; its brief carries a `companion_angle`
(one observation · the origin story · the central tension · one example · why it was
written · a related distinct angle). The evaluator judges each piece independently, then
in **bundle mode**: coherence, whether the companion drives interest in the long-form piece,
whether it stands alone, whether the two are unnecessarily repetitive, channel fit.
Bounded: two members in V1.

---

## The draft packet

Each single draft produces a **draft packet** (a long-form + companion pair will later
produce a **bundle packet**). It carries the paste-ready draft, a scorecard (Voice +
Positioning Impact, must-fixes applied, declined suggestions with reasons), Questions for
you, and the **editorial confidence section** authored by the evaluator (Why CHAIN chose
this · What this communicates · Why you have standing to say it · Reasonable publication
risk · Editorial verdict). Candid and evidence-based; never instructed to persuade you a
draft is good. Full anatomy in [packet.md](packet.md); a synthetic example is in
[examples/sample-draft-packet.md](../examples/sample-draft-packet.md).

---

## Runs are configurable

A run spec sets: number of pieces, allowed formats, default channel, whether long-form
is allowed, whether long-form auto-receives a companion, and whether ideas come from
Discover, the backlog, a user input, or a mix. The **first proof-of-concept preset**
produces **five short/medium LinkedIn-ready pieces**
([examples/runs/five-linkedin.yaml](../examples/runs/five-linkedin.yaml)). The engine
also supports (but the first run doesn't require) a directed premise, one long-form piece, a
long_form+companion bundle, and expanding an existing piece.

---

## One backlog (V1, deliberately un-clever)

There is **one main ideas backlog** (`ideas.csv`). Everything flows into it: your
manually entered ideas, ideas harvested from any marked source (e.g. job applications or
a notes file), unfinished
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
configurable runs; generic marker-based idea harvesting (job applications are one example).

See [future-work.md](future-work.md) for what is intentionally deferred.
