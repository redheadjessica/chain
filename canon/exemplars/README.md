# Exemplars

Annotated reference pieces the writer drafts toward and the evaluator compares
against — a **gold** example (what great looks like) and a **negative** example (what
failure looks like), tagged by `(channel, format)`.

## Public vs private

This repo ships **synthetic** exemplars only (a fictional persona), so the public
demo runs and contributors can see the format. **Your real gold/negative exemplars —
drawn from your own posts — live in your `chain_home`**, not in git, because your
corpus is personal. You replace the synthetic exemplars with your own.

## File shape (when added)

```
# Exemplar: <short label>  ·  channel: linkedin  ·  format: short_form
**Status: GOLD | NEGATIVE.**

**Why it's gold / why it fails:**
- <annotation>
- <annotation>

---
<the piece text>
```

*(No exemplar files are committed yet — the Draft/Evaluate agents that consume them
are the next implementation slice. Synthetic gold/negative samples will be added
alongside those agents.)*
