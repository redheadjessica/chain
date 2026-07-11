# Channel: LinkedIn

One rule pack among several. Selected by a brief with `channel: linkedin`. Mixes
**mechanical** rules (enforced by `lint_draft.py`) and **judgment** guidance (for the
writer and evaluator). Only the mechanical rules are linted.

## Mechanical (linted)

- Length: ~1,300–3,000 characters for a standard post; short_post leaner.
- First ~2 lines carry the post before the "see more" fold — the linter checks that
  a non-trivial first line exists, **not** whether it's a good hook (that's judgment).
- External links in the body suppress reach → **flag**; route links to the first
  comment. `max_external_links_in_body: 0` by default.
- Hashtags: 0–3, at the end.
- No repeated punctuation (`!!!`, `??`).
- Emoji allowed (this is public voice, unlike a cover letter).
- Whitespace is formatting: short paragraphs, blank lines between beats.

## Judgment (writer + evaluator, not linted)

- The first line should earn the second. (Strength is the evaluator's call.)
- Plain-spoken, one idea per post; a clear point of view beats balanced hedging.
- A call to action is optional; if present, make it a real invitation, not bait
  ("Agree?", "Thoughts?" as engagement bait is a tell).
- Companion posts for a long-form piece take an angle; they never summarize (see
  `formats/companion_post.md`).

## Packet extras for this channel

- Suggested first comment (for any link).
- Suggested posting window.
