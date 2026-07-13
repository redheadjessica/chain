# Positioning Pillars (template)

The professional impressions your public writing is meant to build. CHAIN's
evaluator scores **Positioning Impact** against these — the primary target, above
engagement. This file ships as an example default; it's a `positioning_pillars`
reference you point at (a copy in `chain_home`, or a file you already keep). Each
piece declares one **primary** pillar and, optionally, one **secondary**.

Keep pillar `id`s stable — briefs, ideas, and pieces reference them by id.

| id | Pillar | A post serves it when… |
|---|---|---|
| `sharp-product-thinker` | Sharp product thinker | it shows real product judgment — a framework, a tradeoff named honestly, a non-obvious call |
| `current-and-fluent` | Current and technically fluent | it demonstrates hands-on command of current tools/techniques, not commentary from the sidelines |
| `full-strength` | Experienced and operating at full strength | it reads as someone doing their best work now, not recounting past glory |
| `distinctive-and-engaging` | Distinctive and engaging | it has a point of view and a voice; it wouldn't be interchangeable with anyone else's post |
| `warm-and-human` | Warm, perceptive, and human | it shows empathy and perception about people, not just systems |
| `high-agency-builder` | High-agency builder | it shows someone who builds and ships, who makes things happen rather than waiting |

## How the evaluator uses this

- A piece is judged on how well it advances its **declared** primary pillar (and
  secondary, if set) — not on hitting all six.
- **"Strategically useful, but currently too generic"** is a real failure mode: a
  clean post that could be anyone's does not advance a pillar and should score low on
  Positioning Impact even if Voice is fine.
- Engagement/resonance is advisory only in V1 and never overrides positioning.

## Customizing

Edit the rows in your own copy. Add, remove, or rename pillars; keep ids stable
once pieces reference them. If you rename an id, run `chain groom` to surface
references that need updating.
