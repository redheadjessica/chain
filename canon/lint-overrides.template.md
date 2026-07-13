# Lint Overrides (template)

`lint_draft.py` ships with a **generic, persona-neutral** rule set. Your *personal*
additions — phrases you never use, tells specific to your writing — live here, in
a file in your `chain_home` (or wherever you keep canon), referenced by your
config's `lint_overrides` key. This ships as an empty template; copy it and point
`lint_overrides` at your copy — `chain.intake` also classifies it as an asset.

The linter is **mechanical only**: it checks observable, deterministic things. Hook
strength, originality, and editorial quality are the evaluator's job, never the
linter's.

## Format

```yaml
# banned exact phrases / regex patterns (added to the generic set)
banned_phrases:
  - "circle back"
  - "at the end of the day"

# words to warn on (allowed, but flagged for a human look)
watch_words:
  - "basically"

# per-channel overrides (merged onto the channel pack)
channels:
  linkedin:
    max_hashtags: 3
    max_external_links_in_body: 0   # links go in the first comment
```

## What the linter checks (mechanical, deterministic)

banned phrases/patterns · punctuation constraints · length ranges · paragraph
structure · external-link rules · hashtag counts · repeated punctuation · required
sections present · format-specific mechanical requirements.

## What it does NOT check (evaluator's job)

hook strength · originality · emotional impact · positioning · whether the piece is
any good.

## Mention vs. use

If a draft *quotes* a banned phrase (e.g. citing it as an example of what to avoid),
the linter auto-detects the surrounding quote marks and downgrades that occurrence
to a `warn`-level "known false positive" instead of blocking the draft as an error.
This is a simple proximity check, not a parser — it looks for a quote character
immediately around the match. A banned phrase used live (not quoted) anywhere in
the draft still errors normally.
