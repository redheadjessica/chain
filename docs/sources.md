# CHAIN — Sources & Intake

CHAIN **adapts to where your writing already lives** and to **how much model-assisted
setup you want to pay for.** You never reorganize anything: you point CHAIN at your
existing folders and it maps them in place, read-only. No source is ever moved or copied
into a permanent CHAIN location.

## Three intake levels (assistance around one mapping)

| Level | You do | CHAIN does | Model cost |
|---|---|---|---|
| **Manual** | state paths, `type`, include/exclude, markers, contents | deterministic indexing | ~none |
| **Assisted** *(recommended)* | confirm/correct a proposal | samples a bounded number of files, proposes a mapping | bounded, tunable (`intake.sample_size`, `intake.model`) |
| **Deep** *(opt-in)* | confirm/correct a proposal | inspects a broader, messier corpus and proposes a mapping | higher — labeled token-intensive |

**Cost model:** organizing your folders and mapping them explicitly costs almost no
tokens; assisted/deep discovery spends tokens to save you manual setup. Pick per your
corpus. These are levels of the *same* source model — not separate systems.

## Mappings are durable; runs are incremental

Assisted/deep run **once** to produce a mapping that is saved back into your config.
Normal runs never re-ask a model to rediscover structure. An **ingestion ledger**
(`chain_home/state/ingest-ledger.csv`) records each file's content hash and the ideas it
produced, so each run inspects **only new or changed files**, unchanged sources cost
nothing, and re-runs never duplicate ideas. Remap a source whenever you want.

## Configuring a source

```yaml
sources:
  - name: linkedin           # your label
    type: linkedin_posts      # selects the connector
    path: ~/wherever/it/is    # your existing folder (read-only)
    include: ["*.md", "*.txt"]
    exclude: ["**/drafts/**"]
    enabled: true
```

## Roles, not industries

A source declares **roles** — small, generic hints about the kind of signal it carries.
They are how CHAIN reads any domain the same way:

`published` · `drafts` · `questions` · `feedback` · `reviews` · `research` · `projects`
· `offers` · `audience-needs` · `idea-source` · `reference` · `changes` · `custom`

A source may list several; unknown roles are allowed (they pass to the Discover agent).
`type` is a free reading-behavior label (`text` is the generic default; `linkedin_posts`,
`longform`, `website`, `repo`, `job_applications`, `backlog` are conveniences) — in V1
all text sources read alike, so **roles**, not `type`, carry the meaning.

Examples across domains (same mechanism):

| Source | roles | Domain |
|---|---|---|
| published essays / posts | `published` | any |
| FAQs / client questions / application answers | `questions`, `audience-needs` | product person, studio, clinic |
| reviews / testimonials | `reviews`, `feedback` | service business |
| project repo / changelog | `projects`, `changes` | any builder |
| consultation or working notes | `reference`, `changes` | studio, consultancy |

## Two kinds of ingestion

- **Corpus read** — sources contribute normalized excerpts the Discover lenses scan for
  patterns.
- **Idea harvest** — *any* source with a configured `idea_marker` heading has its
  explicitly-listed ideas extracted into the backlog. A job-applications folder whose
  files carry a "Writing ideas" section is just one example; a notes file with an "Ideas"
  heading works identically. No filename or wording is hard-coded, and no special
  connector is required.

## Recommended layout for brand-new users (example only — never required)

Keep your material wherever it already lives and point `path` at it. Adapting to your
structure is a core design principle — see
[architecture.md](architecture.md#design-principles).

## Format discipline (V1)

Text-extractable formats (`.md`, `.txt`) are first-class. `.pages` is macOS-only and
`.pdf` / `.docx` extraction is messy and platform-specific — treat them as best-effort
and prefer exporting text. CHAIN ships no document-extraction subsystem in V1.

## Privacy

Sources are read-only and never copied into git or into a permanent CHAIN location.
What CHAIN derives from them lands only in the gitignored `chain_home/workspace/`. See
[privacy.md](privacy.md).
