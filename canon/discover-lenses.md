# Discover Lenses

Reusable editorial patterns the Discover agent scans a corpus for. They are
**domain-agnostic**: they describe shapes of ideas, not any industry. A product
person's job applications, a studio's client questions, and a nonprofit's donor
feedback all fit the same lenses. Each lens key is stable — seeds reference it.

| key | Pattern | Fires when… |
|---|---|---|
| `repeated-question` | Repeated question or tension | the same question, objection, need, or problem appears across sources |
| `converging-signal` | Converging signal | multiple sources point to the same audience interest, need, capability, concern, or theme |
| `fresh-lesson` | Fresh lesson | recent work, changes, decisions, or experiences contain a useful lesson |
| `old-meets-now` | Old meets now | older material becomes newly relevant given current work or context |
| `latent-pov` | Latent point of view | the author has repeatedly implied a position without stating it directly |
| `expansion-opportunity` | Expansion opportunity | an existing short piece, answer, or note has enough substance to develop further |
| `translation-opportunity` | Translation opportunity | specialist knowledge could be made useful to a broader audience |
| `coverage-guard` | Coverage guard | a topic has been covered enough already — steer away rather than repeat it |

## How the agent uses roles

Each source carries generic **role** hints (`questions`, `feedback`, `reviews`,
`projects`, `changes`, `published`, `offers`, `audience-needs`, `reference`, …). Roles
tell the agent how to read a source without hard-coding any domain:

- `questions` / `feedback` / `reviews` → strong signal for `repeated-question`,
  `converging-signal`, `translation-opportunity`.
- `projects` / `changes` → `fresh-lesson`, `old-meets-now`.
- `published` → the baseline for `coverage-guard` and `expansion-opportunity`.
- `research` / `reference` → `translation-opportunity`, supporting evidence.

Roles are hints, not rules. Unknown roles are fine — the agent interprets them.

## Domain neutrality (required)

The agent must adapt to whatever the sources describe. It must NOT default to career,
job-search, or thought-leadership framing unless the sources and positioning pillars
are actually about that. An idea for a waxing studio should read like the studio's
voice, not like LinkedIn career advice.
