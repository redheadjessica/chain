#!/usr/bin/env python3
"""Source connectors — deterministic, map-in-place readers.

CHAIN adapts to where your material already lives. A connector knows how to walk one
kind of source (by `type`) under your include/exclude rules and yield normalized
records. It never moves or copies your files; it references them in place.

This module is the deterministic core of intake (the "manual mapping" level). Assisted
and deep discovery add a model-backed *proposer* on top that emits the same source
config a human would write by hand — they do not replace this reader.

Two record kinds:
  * indexed file  — path + hash + metadata (the basis for incremental, no-cost re-runs)
  * harvested idea — a writing-idea suggestion extracted from a source (e.g. the
    "Writing ideas" section a job-application file already contains)

Stdlib only.
"""

from __future__ import annotations

import fnmatch
import functools
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

# --- source config ----------------------------------------------------------

KNOWN_TYPES = {
    "linkedin_posts", "longform", "website", "job_applications", "repo", "backlog",
}
# Source types that carry explicit writing-idea suggestions to harvest.
IDEA_HARVEST_TYPES = {"job_applications"}
DEFAULT_IDEA_MARKER = "Writing ideas"


@dataclass
class Source:
    name: str
    type: str
    path: str
    include: list = field(default_factory=lambda: ["*.md", "*.txt"])
    exclude: list = field(default_factory=list)
    idea_marker: str = DEFAULT_IDEA_MARKER
    enabled: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "Source":
        return cls(
            name=d["name"],
            type=d["type"],
            path=str(Path(str(d["path"])).expanduser()),
            include=list(d.get("include") or ["*.md", "*.txt"]),
            exclude=list(d.get("exclude") or []),
            idea_marker=d.get("idea_marker") or DEFAULT_IDEA_MARKER,
            enabled=bool(d.get("enabled", True)),
        )


@dataclass(frozen=True)
class IndexedFile:
    source: str
    path: str          # absolute, canonical location (referenced in place)
    rel_path: str      # relative to the source root (the ledger key)
    sha256: str
    size: int


@dataclass(frozen=True)
class HarvestedIdea:
    source: str
    source_ref: str    # the file the idea came from (rel_path)
    working_title: str
    premise: str


# --- walking ----------------------------------------------------------------

@functools.lru_cache(maxsize=256)
def _compile_glob(pattern: str):
    """Compile a glob with gitignore-style ** semantics: `**/` matches any leading
    directories (including none), `/**` matches any trailing path, `*` stays within a
    path segment. Falls back cleanly for simple patterns like `*.md`."""
    s = re.escape(pattern)
    s = s.replace(r"\*\*/", "(?:.*/)?")   # **/  -> zero or more leading dirs
    s = s.replace(r"/\*\*", "(?:/.*)?")   # /**  -> any trailing path
    s = s.replace(r"\*\*", ".*")          # **   -> anything
    s = s.replace(r"\*", "[^/]*")         # *    -> within a segment
    s = s.replace(r"\?", "[^/]")
    return re.compile("^" + s + "$")


def _matches(rel_posix: str, name: str, patterns) -> bool:
    for p in patterns:
        rx = _compile_glob(p)
        if rx.match(name) or rx.match(rel_posix):
            return True
    return False


def walk_source(source: Source):
    """Yield (abs_path, rel_posix) for files under the source matching include and not
    matching exclude. Missing roots yield nothing (doctor reports them)."""
    root = Path(source.path)
    if not root.exists():
        return
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if source.include and not _matches(rel, p.name, source.include):
            continue
        if source.exclude and _matches(rel, p.name, source.exclude):
            continue
        yield p, rel


def hash_file(path: Path) -> tuple:
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def index_source(source: Source):
    """Yield IndexedFile for every matching file (path + hash + size)."""
    for abs_path, rel in walk_source(source):
        digest, size = hash_file(abs_path)
        yield IndexedFile(source.name, str(abs_path), rel, digest, size)


# --- idea harvesting --------------------------------------------------------

_LIST_ITEM = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s+(.*\S)\s*$")
_HEADING = re.compile(r"^\s*#{1,6}\s*(.*\S)\s*$")


def _title_from(item: str) -> str:
    """A short working title from an idea line: text before an em/en/hyphen dash or a
    colon, else the first ~10 words."""
    head = re.split(r"\s+[—–-]\s+|:\s+", item, maxsplit=1)[0].strip()
    words = head.split()
    if len(words) > 12:
        words = item.split()[:10]
    return " ".join(words).rstrip(".,;:")


def harvest_ideas(text: str, marker: str = DEFAULT_IDEA_MARKER):
    """Extract writing-idea suggestions listed under a heading containing `marker`.
    Deterministic: finds the marker heading, then collects the list items beneath it
    until the next heading. Returns a list of (working_title, premise) tuples."""
    marker_norm = marker.strip().lower()
    lines = text.splitlines()
    ideas, in_section = [], False
    for ln in lines:
        h = _HEADING.match(ln)
        if h:
            in_section = marker_norm in h.group(1).strip().lower()
            continue
        if not in_section:
            continue
        m = _LIST_ITEM.match(ln)
        if m:
            premise = m.group(1).strip()
            if premise:
                ideas.append((_title_from(premise), premise))
        elif ln.strip() and not ln.startswith(" "):
            # a non-list, non-indented prose line ends a simple list section
            if ideas:
                in_section = False
    return ideas


def harvest_source(source: Source):
    """Yield HarvestedIdea for every idea found in an idea-harvest source."""
    if source.type not in IDEA_HARVEST_TYPES:
        return
    for abs_path, rel in walk_source(source):
        try:
            text = Path(abs_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for title, premise in harvest_ideas(text, source.idea_marker):
            yield HarvestedIdea(source.name, rel, title, premise)
