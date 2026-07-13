# Intake Interview Guide

The elicitation playbook the `chain-intake` agent uses when an asset is partial or
missing. Domain-agnostic: the same questions work for a product person, a studio
owner, a clinician, a consultant. **Ask only what the current asset needs — never run
this as one giant questionnaire.**

## Ground rules

1. **Three states, always.** Before creating anything, ask whether it exists somewhere
   you haven't seen ("Do you have anything like a style note, even an old one, even
   half-wrong?"). Locate beats improve beats create.
2. **Smallest useful version.** Every asset has a 15-minute version worth shipping.
   Perfect is a later run's problem; the manifest tracks `last_reviewed` for revisits.
3. **Evidence over self-report.** People describe their voice aspirationally. Whenever
   material exists, derive from it and have them react ("keep / wrong / more like
   this") — reactions are far more reliable than descriptions.
4. **Preserve provenance.** Raw material used to distill an asset gets kept (pointed
   at, or copied into a `source-docs/` folder beside the distilled file) with a note
   on where it came from. Distilled files supersede sources at runtime.
5. **Their words outrank your summary.** When the user says something in their own
   phrasing, keep the phrasing. A voice spec that quotes its owner is stronger than
   one that paraphrases them.

## Per-asset elicitation

### Source map (Level 2 especially)
- "Where does material about your work already live — folders, exports, notes apps,
  old sites?" (For cloud tools: export first; V1 reads local text files.)
- Sample a few files per location and PROPOSE the classification (published / drafts /
  questions / feedback / reviews / reference / idea-source); have them confirm.
- Emit the result as a ready-to-paste `sources:` YAML block. Never relocate anything.

### Representative writing / corpus
- Level 1-2: "Which 5-10 existing pieces sound most like you at your best?"
- Level 3 (writing exercises — 10-20 minutes total, these become the seed corpus):
  1. "Retell, in writing, a story you already tell out loud — the way you'd tell a
     smart friend. 150-250 words. Don't polish."
  2. "What's a question people always ask you? Answer it in writing, exactly how
     you'd answer in person."
  3. "What's one piece of common advice in your field you think is wrong? Say why,
     in a short paragraph."
- Save exercises to a samples folder (user's choice of location), map it as a source
  with role `samples`.

### Voice & style guidance
- With material: draft the spec FROM their corpus/samples; mark every inference
  "(inferred — confirm)". Review pass: keep / wrong / more-like-this per section.
- Without material: run the exercises above FIRST, then draft from those.
- Interview supplements: "Whose writing do you admire, and what specifically?" ·
  "What do editors/AI tools keep doing to your text that you hate?" (that answer
  usually IS the anti-patterns starter) · "Read this sentence aloud — would you say
  it?" (the say-it-aloud test transfers into the spec as a standing check).

### Positioning / reputation signals
- The one question that matters: **"After six months of reading you, what should
  someone believe about you?"** Push past adjectives to beliefs ("she's smart" →
  "she's actually building with this stuff, not commenting on it").
- 3-6 pillars, each: stable id, label, "a piece serves it when…" evidence line.
- Distinguish from themes explicitly: pillars = what readers conclude; themes = what
  the writing is about. Don't let topic lists masquerade as positioning.

### Editorial themes
- "What do you actually think about in the shower / talk about unprompted?"
- Mine the corpus and questions-role sources for recurring territories; propose,
  don't dictate. Mark it "expected to evolve".

### Anti-patterns / hard no's
- "Show me writing in your field that makes you cringe. What exactly is wrong?"
- "What would embarrass you if it went out under your name?"
- Personal ones only — generic AI tells already live in the channel packs and linter.

### Audience & outcomes
- "Who do you picture reading this? What do they come to you for?"
- "Be honest: what should a year of public writing change for YOU?" (clients,
  credibility, a move, a community). The honest answer shapes evaluation.

### Optional assets (offer once, don't push)
- Story bank: "What 3-5 true stories do you tell over and over? Let's pin the facts
  so nothing ever gets embellished."
- Exemplar index: "Pick your 3-8 favorites; one line each on why."
- Feedback ledger: create empty; explain it grows from their reactions.
- Principles / channel guidance: only when a real judgment call or channel friction
  has already surfaced.

## Review cadence

End every asset with a 60-second review, not a document dump: show the distilled
result, ask for keep / wrong / more-like-this, apply, move on. One final progress
summary at the end of the whole session — never a review queue per asset.
