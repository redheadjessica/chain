# CHAIN — The Draft Packet

Every finalized draft arrives as a **draft packet**: the paste-ready text plus a candid,
evidence-based case for (or against) publishing. It supports the publication decision
without becoming a hype machine. The **evaluator** authors the judgment sections, so
the writer never grades its own work. (A long-form + companion pair will later produce a
**bundle packet** — the next slice, not this one.)

A committed synthetic example lives at
[`examples/sample-draft-packet.md`](../examples/sample-draft-packet.md); real draft
packets stay under the private `chain_home/workspace/`.

## Anatomy

```
# <working title> — <format> · <channel>

## The draft
<paste-ready text>
(channel-conditional extras, e.g. LinkedIn: suggested first comment for any link,
 suggested posting window)

## Scorecard
Positioning Impact <n>/5 · Voice <n>/5 — <n> must-fix, all resolved · lint clean

## Why CHAIN chose this
- why the idea is worth writing
- which source patterns / materials led to it
- why it is relevant now
- how it differs from what you've already covered

## What this communicates about you
- primary positioning pillar
- optional secondary pillar
- what a relevant hiring manager or product leader may learn about you

## Why you have standing to say it
- the experience, work, or existing writing that makes the point feel earned

## Reasonable publication risk
- the most plausible way it could be misunderstood
- whether that reflects a real communication problem
- whether a clarification is needed, or it is simply the unavoidable exposure of an opinion

## Editorial verdict
<one of the five verdicts>

## Questions for you
<open questions + declined-fix disagreements; "None" if empty>
```

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

The bundle packet ships in the bundle slice; the single-draft packet above is built now
([`chain/produce.py`](../chain/produce.py)).
