#!/usr/bin/env python3
"""Deterministic draft lint — the mechanical gate, before and around the evaluator.

Enforces ONLY observable, mechanical requirements. It never judges whether an opening is
compelling, whether an idea is original or interesting, its positioning value, emotional
impact, or whether the author has standing — those are the evaluator's job.

Rule packs are selected by the brief's `format` and `channel`. This slice ships the two
packs the validation needs (short_form + linkedin, long_form + neutral/medium); the
structure is extensible (add a dict entry, not code). Personal banned phrases come from
an optional overrides dict (from the user's chain_home), so the shipped rules stay
persona-neutral.

Preservation mode (`prev` + `touchpoints`) is the anti-smoothing check for revisions:
only the passages the evaluator cited may change; links must not silently vanish.

Stdlib only.
"""

from __future__ import annotations

import re
from pathlib import Path

MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")

# Quote characters used to detect a MENTION ("the word 'leverage' is banned") vs a
# live USE (leveraging our synergies) of a banned phrase. Deliberately simple — a
# proximity heuristic, not a parser. See _is_quoted_mention.
QUOTE_CHARS = '"\'“”‘’'

# Generic, persona-neutral AI-fingerprint phrases (mechanical, high-precision only).
GENERIC_BANNED = [
    (r"\bdelve\w*\b", 'AI-tell vocab: "delve"'),
    (r"\bleverag(e|ing|ed|es)\b", 'AI-tell vocab: "leverage" (verb) — use "use"'),
    (r"\butiliz(e|ing|ed|es)\b", 'AI-tell vocab: "utilize" — use "use"'),
    (r"\bin today's\b", 'AI-tell opener: "in today\'s ..."'),
    (r"\bin an era\b", 'AI-tell opener: "in an era ..."'),
    (r"\bfurthermore\b", 'AI-tell transition: "furthermore"'),
    (r"\bmoreover\b", 'AI-tell transition: "moreover"'),
    (r"\ba testament to\b", 'AI-tell phrase: "a testament to"'),
    (r"\bit's worth noting\b", 'AI-tell filler: "it\'s worth noting"'),
    (r"\bunlock the potential\b", 'AI-tell phrase: "unlock the potential"'),
]

# Format packs: length bounds (words) + required structure. Mirrors canon/formats/.
FORMAT_PACKS = {
    "short_form": {"min_words": 25, "max_words": 320},
    "long_form": {"min_words": 350, "max_words": 2600},
    "companion_post": {"min_words": 25, "max_words": 320},
    "custom": {"min_words": 0, "max_words": 100000},
}

# Channel packs: mechanical channel rules. Mirrors canon/channels/.
CHANNEL_PACKS = {
    "linkedin": {"max_body_links": 0, "max_hashtags": 5, "emoji_ok": True},
    "neutral": {"max_body_links": 99, "max_hashtags": 99, "emoji_ok": True},
    "medium": {"max_body_links": 99, "max_hashtags": 6, "emoji_ok": True},
}


def _finding(level, code, message):
    return {"level": level, "code": code, "message": message}


def _is_quoted_mention(prose: str, start: int, end: int) -> bool:
    """True if the match at [start:end) is immediately quoted — a MENTION of the
    phrase, not a live use of it. Simple proximity check, not a parser: the char
    right before the match must be a quote, and a quote must appear within a few
    trailing punctuation characters after it."""
    before = prose[max(0, start - 1):start]
    if not before or before[-1] not in QUOTE_CHARS:
        return False
    tail = prose[end:end + 5]
    for ch in tail:
        if ch in QUOTE_CHARS:
            return True
        if ch not in ",;:. -":
            break
    return False


def load_lint_overrides(path) -> dict:
    """Load a user's personal lint overrides (banned_phrases/watch_words/channels)
    from a YAML file outside the repo. Missing/unset path -> {} (generic behavior
    unaffected) — the shipped linter stays persona-neutral by default."""
    p = Path(str(path)).expanduser() if path else None
    if not p or not p.exists():
        return {}
    import yaml
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {
        "banned_phrases": list(data.get("banned_phrases") or []),
        "watch_words": list(data.get("watch_words") or []),
        "channels": dict(data.get("channels") or {}),
    }


def _channel_pack(channel: str, overrides: dict) -> dict:
    base = dict(CHANNEL_PACKS.get(channel, CHANNEL_PACKS["neutral"]))
    over = (overrides or {}).get("channels", {}).get(channel, {})
    if "max_external_links_in_body" in over:   # template's public field name
        base["max_body_links"] = over["max_external_links_in_body"]
    for k in ("max_hashtags", "emoji_ok", "max_body_links"):
        if k in over:
            base[k] = over[k]
    return base


def prose_and_links(text: str):
    links = [(m.group(1), m.group(2)) for m in MD_LINK.finditer(text)]
    prose = MD_LINK.sub(r"\1", text)
    prose = re.sub(r"https?://\S+", " ", prose)
    return prose, links


def _sentences(prose: str):
    parts = re.split(r"(?<=[.!?])\s+", prose)
    return [p.strip() for p in parts if len(re.findall(r"[A-Za-z']+", p)) >= 4]


def lint_draft(text, *, fmt="short_form", channel="neutral", overrides=None,
               prev=None, touchpoints=None):
    """Return (findings, stats). Errors block; warnings inform."""
    overrides = overrides or {}
    prose, links = prose_and_links(text)
    words = len(re.findall(r"[A-Za-z0-9']+", prose))
    findings = []

    fp = FORMAT_PACKS.get(fmt, FORMAT_PACKS["custom"])
    cp = _channel_pack(channel, overrides)

    # --- required content ---
    if not prose.strip():
        findings.append(_finding("error", "empty", "draft body is empty"))

    # --- length bounds ---
    if words > fp["max_words"]:
        findings.append(_finding("error", "too-long",
                                 f"{words} words > {fp['max_words']} max for {fmt}"))
    elif words < fp["min_words"]:
        findings.append(_finding("warn", "too-short",
                                 f"{words} words < {fp['min_words']} suggested for {fmt}"))

    # --- banned phrases (generic + personal overrides) ---
    # Each OCCURRENCE is classified separately: a live use is an error; a match
    # immediately wrapped in quotes (citing the phrase, not using it) is auto-
    # classified as a known false positive and downgraded to warn, per-occurrence —
    # so a draft that both quotes and uses a banned phrase gets both right.
    for pat, msg in GENERIC_BANNED:
        for m in re.finditer(pat, prose, re.IGNORECASE):
            if _is_quoted_mention(prose, m.start(), m.end()):
                findings.append(_finding(
                    "warn", "banned-phrase-quoted-mention",
                    f"{msg} — quoted mention, not a live use (auto-classified false positive)"))
            else:
                findings.append(_finding("error", "banned-phrase", msg))
    for phrase in overrides.get("banned_phrases", []):
        for m in re.finditer(re.escape(phrase), prose, re.IGNORECASE):
            if _is_quoted_mention(prose, m.start(), m.end()):
                findings.append(_finding(
                    "warn", "banned-phrase-quoted-mention",
                    f'personal banned phrase: "{phrase}" — quoted mention, not a live use '
                    "(auto-classified false positive)"))
            else:
                findings.append(_finding("error", "banned-phrase", f'personal banned phrase: "{phrase}"'))
    for phrase in overrides.get("watch_words", []):
        if re.search(re.escape(phrase), prose, re.IGNORECASE):
            findings.append(_finding("warn", "watch-word", f'watch word: "{phrase}"'))

    # --- repeated punctuation ---
    if re.search(r"[!?]{2,}", prose):
        findings.append(_finding("error", "repeated-punct", "repeated punctuation (!! or ??)"))

    # --- channel link rules ---
    if len(links) > cp["max_body_links"]:
        findings.append(_finding(
            "error", "body-links",
            f"{len(links)} inline link(s) in body; {channel} allows {cp['max_body_links']} "
            "(put links in the first comment / footnote)"))

    # --- hashtags ---
    n_tags = len(re.findall(r"(?:^|\s)#\w+", text))
    if n_tags > cp["max_hashtags"]:
        findings.append(_finding("warn", "hashtags",
                                 f"{n_tags} hashtags > {cp['max_hashtags']} for {channel}"))

    # --- preservation mode (anti-smoothing during revision) ---
    if prev is not None:
        p_prose, p_links = prose_and_links(prev)
        prev_urls = {u for _, u in p_links}
        for lost in prev_urls - {u for _, u in links}:
            findings.append(_finding("error", "smoothing",
                                     f"link removed in revision: {lost} (links may move, not vanish)"))
        tps = [t.lower() for t in (touchpoints or [])]
        new_sentences = _sentences(prose)
        for sent in _sentences(p_prose):
            if _is_cited(sent.lower(), tps):
                continue  # this sentence was cited for change — allowed to move
            if any(_text_overlap(sent.lower(), c.lower()) for c in new_sentences):
                continue  # content survived intact, even if merged/reworded nearby
            best = max((_ratio(sent, c) for c in new_sentences), default=0.0)
            if best < 0.7:
                findings.append(_finding(
                    "error", "smoothing",
                    f'uncited sentence changed/removed in revision: "{sent[:60]}..." '
                    "(surgeon rule: touch only cited passages)"))

    return findings, {"words": words, "links": len(links), "hashtags": n_tags}


def _ratio(a, b):
    import difflib
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _text_overlap(a_lower: str, b_lower: str) -> bool:
    """True if a's content is essentially contained in b, or vice versa — either a
    literal substring (handles a quote spanning multiple sentences, or several
    sentences merging into one) or high token overlap (handles light rewording).
    Deliberately generous: this recognizes "this content survived" without relying
    on whole-string character ratio, which false-positives whenever a merge or a
    multi-sentence quote dilutes the two strings' relative lengths."""
    if not a_lower or not b_lower:
        return False
    if a_lower in b_lower or b_lower in a_lower:
        return True
    a_words = set(re.findall(r"[a-z']+", a_lower))
    b_words = set(re.findall(r"[a-z']+", b_lower))
    return bool(a_words) and len(a_words & b_words) / len(a_words) >= 0.6


def _is_cited(sent_lower: str, touchpoints_lower: list) -> bool:
    """True if a (lowercased) sentence was cited by a finding's quote — a quote that's
    a fragment WITHIN one sentence (the common case), or one that SPANS multiple
    original sentences (the evaluator cited "X. Y." across a sentence boundary)."""
    return any(_text_overlap(sent_lower, tp) for tp in touchpoints_lower)


def has_errors(findings):
    return any(f["level"] == "error" for f in findings)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="CHAIN deterministic draft lint")
    ap.add_argument("file")
    ap.add_argument("--format", default="short_form")
    ap.add_argument("--channel", default="neutral")
    ap.add_argument("--prev", help="previous draft — enables preservation checks")
    args = ap.parse_args(argv)
    text = Path(args.file).read_text(encoding="utf-8")
    prev = Path(args.prev).read_text(encoding="utf-8") if args.prev else None
    findings, stats = lint_draft(text, fmt=args.format, channel=args.channel, prev=prev)
    print(f"lint: {args.file}  ({stats['words']} words, {stats['links']} links)")
    for f in findings:
        print(f"  {f['level'].upper()}: {f['message']}")
    errs = sum(1 for f in findings if f["level"] == "error")
    print(f"  => {errs} error(s), {len(findings) - errs} warning(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
