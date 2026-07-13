# CHAIN — The Draft Packet

Every finalized draft arrives as a **draft packet**: the paste-ready text plus a candid,
evidence-based case for (or against) publishing. It supports the publication decision
without becoming a hype machine. The **evaluator** authors the judgment sections, so
the writer never grades its own work. (A long-form + companion pair will later produce a
**bundle packet** — the next slice, not this one.)

A committed synthetic example lives at
[`examples/sample-draft-packet.md`](../examples/sample-draft-packet.md); real draft
packets land under the private `__READY_TO_REVIEW__PRIVATE_GITIGNORED/`.

## Anatomy

```
# <working title> — <format> · <channel>

## The draft
<paste-ready text>

## What shaped this draft
- Idea + Piece id, format/channel
- how this idea was selected (automatic / user-directed / manual, with the factors —
  or an honest "not recorded" if no selection event was logged)
- voice guidance, positioning guidance, lint overrides, and feedback ledger consulted
  (paths/names — never full excerpts)
- source materials referenced (source:ref list)
- exemplars referenced, or "None referenced this run"

## Scorecard
- Voice <n>/5 · Positioning Impact <n>/5
- Pre-revision verdict (what the FIRST draft would have scored)
- Findings this run, by severity: must-fix / improvement / protect / consideration

## Revision
- Findings addressed (by id, with what changed)
- Findings declined (by id, with the writer's reason — includes any declined
  must-fix, flagged loudly, never silently dropped)
- Protected language (evaluator-marked passages; mechanically verified to survive
  verbatim in the final text)
- Questions for you

## Final lint status
- clean, OR the unresolved error(s)
- known false positives auto-classified (e.g. a banned phrase used only as a quoted
  example, not a live use) — shown, not hidden
- any other flags (e.g. a revision-integrity note)

## Why CHAIN chose this
## What this communicates
## Why you have standing to say it
## Reasonable publication risk

## Editorial verdict
<one of the five verdicts>

## What CHAIN may learn from this run
- what CHAIN may retain if you feed it back (your final edit, explicit feedback,
  approved reusable lessons)
- what it will NOT auto-learn (its own draft, evaluator opinions alone, unapproved
  inferred preferences, rejected language reappearing)
```

## The loop is always Draft → Evaluate → Revise → Reevaluate

The bounded revision pass always runs, even on a draft that scores 5/5 with zero
must-fix findings — the evaluator is expected to surface *something* (an improvement,
a protect note) on nearly every draft. A revision that changes nothing is a valid but
rare outcome, and only legitimate when every finding was explicitly declined with a
reason; the packet says so plainly rather than silently showing `draft-v1.md` and
`final.md` as identical.

## Every draft packet is a persisted Piece

Reaching a packet is not the end of the story for the library: `run_production`
always persists a `PIECE-xxxx` row (status `final`, never `published` — that's your
call) and advances the originating Idea past `proposed`/`developing` to `produced`.
One Idea may produce several Pieces over time, in different formats — a short-form
Piece never blocks the same Idea from later producing a long-form one.

## The five verdicts

- **Strong candidate to publish**
- **Good candidate with one issue to review**
- **Interesting but somewhat exposed**
- **Strategically useful, but currently too generic**
- **Do not publish this version**

## The honesty rule

The confidence section is candid and evidence-based and is **never** instructed to
persuade you a piece is good. "Do not publish this version" and "too generic" are
normal, healthy outputs. A run whose packets are uniformly glowing is itself a signal
the evaluator has drifted toward flattery — the rubric is tuned against that.

## Bundles

An `{long_form + companion_post}` bundle adds a **pair section**: does the companion
create interest in the long-form piece, does it stand alone, are the two unnecessarily
repetitive, does each fit its channel. Authored by the evaluator's bundle mode.

Both are built now — the single-draft packet in [`chain/produce.py`](../chain/produce.py)
and the bundle packet in [`chain/bundle.py`](../chain/bundle.py). A synthetic bundle
example is in
[`examples/sample-bundle-packet.md`](../examples/sample-bundle-packet.md).
