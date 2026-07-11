#!/usr/bin/env python3
"""Corpus normalization — turn changed source files into a compact, reusable index.

Produces a normalized index the Discover agent reads instead of raw files: one entry
per document with its title, a bounded excerpt, word count, roles, and content hash.
This is NOT a copy of your corpus — it stores narrow excerpts and metadata only, and
reuses cached entries for files whose hash hasn't changed (so only new/changed
material is re-read).

Stdlib only.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .sources import Source, hash_file, walk_source

EXCERPT_CHARS = 900


@dataclass
class DocIndex:
    source: str
    ref: str
    roles: list = field(default_factory=list)
    title: str = ""
    excerpt: str = ""
    words: int = 0
    sha256: str = ""


def _title_of(text: str, fallback: str) -> str:
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        m = re.match(r"^#{1,6}\s*(.+\S)\s*$", s)
        return (m.group(1) if m else s)[:120]
    return fallback


def _excerpt_of(text: str) -> str:
    body = re.sub(r"\s+", " ", text).strip()
    return body[:EXCERPT_CHARS]


def _cache_path(config: dict) -> Path:
    return Path(config["chain_home"]) / "cache" / "corpus-index.json"


def build_corpus_index(config: dict, *, use_cache: bool = True) -> list:
    """Return a list of DocIndex dicts for all enabled sources, reusing cached excerpts
    for unchanged files. Writes the index to chain_home/cache/corpus-index.json."""
    cache_path = _cache_path(config)
    prev = {}
    if use_cache and cache_path.exists():
        for e in json.loads(cache_path.read_text(encoding="utf-8")):
            prev[(e["source"], e["ref"])] = e

    out = []
    for sd in config.get("sources", []):
        source = Source.from_dict(sd)
        if not source.enabled or not Path(source.path).exists():
            continue
        for abs_path, rel in walk_source(source):
            digest, _ = hash_file(abs_path)
            cached = prev.get((source.name, rel))
            if cached and cached.get("sha256") == digest:
                cached["roles"] = list(source.roles)  # roles may change without content
                out.append(cached)
                continue
            try:
                text = Path(abs_path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            out.append(asdict(DocIndex(
                source=source.name, ref=rel, roles=list(source.roles),
                title=_title_of(text, rel), excerpt=_excerpt_of(text),
                words=len(text.split()), sha256=digest,
            )))

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out
