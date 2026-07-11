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

## Supported source types (V1)

| `type` | What it is | Expected shape | Feeds |
|---|---|---|---|
| `linkedin_posts` | Your published short-form archive | one file per post; text/markdown | corpus + overuse baseline |
| `longform` | Medium / Substack / essays | one file per piece | corpus |
| `website` | Exported site / page content | text/markdown/html | corpus |
| `job_applications` | One subfolder per application | text/markdown; a heading marking suggested writing ideas | **idea harvest** + corpus |
| `repo` | A project repository | markdown, CHANGELOG | corpus ("what changed → lesson") |
| `backlog` | An optional hand-kept idea list | one markdown/CSV file | idea seeds (one source among many) |

## Two kinds of ingestion

- **Corpus read** — most sources contribute normalized text the Discover lenses scan
  for patterns.
- **Idea harvest** — `job_applications` additionally extracts the 1–3 writing-idea
  suggestions your job-application agent already emits, found by a **configurable
  `idea_marker` heading** (default `"Writing ideas"`) so no filename or wording is
  hard-coded. Each becomes an idea seed (`source_type=job-application`).

## Recommended layout for brand-new users (example only — never required)

If you're starting from scratch and want a suggestion:

```
~/writing/linkedin/      ~/writing/longform/      ~/applications/<company>/
```

But if your writing already lives somewhere else, keep it there and point `path` at
it. Adapting to your structure is a core design principle — see
[architecture.md](architecture.md#design-principles).

## Format discipline (V1)

Text-extractable formats (`.md`, `.txt`) are first-class. `.pages` is macOS-only and
`.pdf` / `.docx` extraction is messy and platform-specific — treat them as best-effort
and prefer exporting text. CHAIN ships no document-extraction subsystem in V1.

## Privacy

Sources are read-only and never copied into git or into a permanent CHAIN location.
What CHAIN derives from them lands only in the gitignored `chain_home/workspace/`. See
[privacy.md](privacy.md).
