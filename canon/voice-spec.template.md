# Voice Spec (template)

The **writer's canon** for your voice, written for an AI agent, not a human reader.
This ships as a generic template; it's a `voice_spec` reference you point at — a copy
in `chain_home`, or a style file you already keep. Replace the placeholders with your
own voice. Your real voice-spec is private (it encodes personal style) and lives
outside git.

Channel- and format-specific mechanics live in [`canon/channels/`](channels/) and
[`canon/formats/`](formats/); this file is the channel-neutral core.

---

## The north star

The reader should finish thinking: *a real, specific person wrote this, and they
know what they're talking about* — not *this was optimized for the feed*. A little
friction, a real example, an uneven rhythm are trust signals. Polish is cheap; a
person on the page is rare.

## Default register (customize this whole section)

> Replace with 3–5 lines describing how you actually sound: direct? warm? funny?
> proof-backed? The evaluator compares drafts against this and against your exemplars.

## Hard rules (mechanical — also enforced by `lint_draft.py`)

> These are examples. Keep the ones that match your voice; the linter enforces
> whatever is listed in `canon/lint-overrides.template.md` + the channel packs.

- Contractions by default; an uncontracted phrase only to emphasize a genuinely
  strong point.
- No em dashes, no semicolons (commas, periods, parentheses, colon instead).
- Say the point once, plainly. No "not just X but Y" scaffolding, no false
  equivalences, no repeated three-item abstraction lists.
- No AI-fingerprint vocabulary (delve, leverage-as-verb, "proven track record",
  "meaningful impact", "in today's …", "furthermore/moreover", etc.).
- Energy is voice, not a defect. Keep enthusiasm where it's real.

## Truth discipline

- No fabrication. Every claim traces to your real experience, work, or existing
  writing (the **standing** check in the packet).
- If a piece wants a claim you can't support, reframe honestly or leave it out.
  Uncertainties go to the packet's "Questions for you", not into hedged prose.

## Anti-smoothing (revision passes)

Be a surgeon, not an editor: touch only the lines the evaluation cited; everything
else survives verbatim. "Smoother" is not "better" — evenly polished text is the
tell. Keep sentence rhythm uneven.
