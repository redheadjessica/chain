#!/usr/bin/env python3
"""Discover Synthesis harness (deterministic parts).

The creative step — proposing idea seeds from the corpus — is done by the portable
`chain-discoverer` agent (an LLM), injected here as `agent_fn`. Everything around it is
deterministic Python:

  build_discoverer_input  -> assemble the agent's JSON input from the normalized corpus
  run_discoverer          -> call the injected agent, validate its output shape
  select_seeds            -> a lightweight, DETERMINISTIC pick (dedup + diversify + cap)
  seeds_to_backlog        -> add selected seeds to the one backlog via existing dedup
  develop_briefs          -> package selected ideas into briefs (deterministic assembly)

Honesty note: the seeds' premises, lenses, evidence, and any quality judgment come from
the LLM. `select_seeds` does NOT re-score seed quality — it only removes duplicates and
spreads the pick across lenses/pillars. So selection is deterministic; the *ideas* are
not.

Stdlib only.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from .editorial_library import EditorialLibrary

# Mirrors canon/discover-lenses.md (that file is the human source of truth).
LENSES = [
    ("repeated-question", "the same question, objection, need, or problem recurs across sources"),
    ("converging-signal", "multiple sources point to the same audience interest, need, capability, concern, or theme"),
    ("fresh-lesson", "recent work, changes, decisions, or experiences contain a useful lesson"),
    ("old-meets-now", "older material becomes newly relevant given current work or context"),
    ("latent-pov", "the author repeatedly implies a position without stating it directly"),
    ("expansion-opportunity", "an existing short piece, answer, or note has substance to develop further"),
    ("translation-opportunity", "specialist knowledge could be made useful to a broader audience"),
    ("coverage-guard", "a topic is already covered enough — steer away rather than repeat it"),
]
LENS_KEYS = {k for k, _ in LENSES}


# --- pillars ----------------------------------------------------------------

def parse_pillars(pillars_path) -> list:
    """Parse `| `id` | Label |` rows from a positioning-pillars markdown file."""
    out = []
    p = Path(str(pillars_path)) if pillars_path else None
    if not p or not p.exists():
        return out
    for ln in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*`?([a-z0-9][a-z0-9-]*)`?\s*\|\s*([^|]+?)\s*\|", ln)
        if m and m.group(1) != "id":
            out.append({"id": m.group(1), "label": m.group(2).strip()})
    return out


# --- input assembly ---------------------------------------------------------

def build_discoverer_input(config: dict, corpus_index: list, library: EditorialLibrary,
                           *, max_seeds: int = 8) -> dict:
    by_source: dict = {}
    for doc in corpus_index:
        by_source.setdefault(doc["source"], {"name": doc["source"],
                                             "roles": doc.get("roles", []), "docs": []})
        by_source[doc["source"]]["docs"].append({
            "ref": doc["ref"], "title": doc.get("title", ""),
            "excerpt": doc.get("excerpt", ""),
        })
    return {
        "positioning_pillars": parse_pillars(config.get("positioning_pillars")),
        "lenses": [{"key": k, "pattern": d} for k, d in LENSES],
        "sources": list(by_source.values()),
        "existing_idea_titles": [r["working_title"] for r in library.active_ideas()],
        "max_seeds": max_seeds,
    }


# --- run the (injected) agent ----------------------------------------------

def _validate_output(raw) -> dict:
    if not isinstance(raw, dict) or not isinstance(raw.get("seeds"), list):
        raise ValueError("discoverer output must be an object with a 'seeds' list")
    for i, s in enumerate(raw["seeds"]):
        for req in ("working_title", "premise", "lens", "evidence"):
            if req not in s:
                raise ValueError(f"seed {i} missing '{req}'")
        if not isinstance(s["evidence"], list):
            raise ValueError(f"seed {i} 'evidence' must be a list")
    raw.setdefault("coverage_notes", [])
    return raw


def run_discoverer(agent_input: dict, agent_fn) -> dict:
    """agent_fn(input_dict) -> output_dict (the LLM). Returns validated output."""
    return _validate_output(agent_fn(agent_input))


# --- deterministic selection ------------------------------------------------

def select_seeds(seeds: list, library: EditorialLibrary, *, max_n: int = 5,
                 per_lens_cap: int = 2):
    """Deterministic pick: drop exact backlog duplicates, spread across lenses/pillars,
    cap at max_n. Does not re-rank seed quality. Returns (selected, skipped)."""
    selected, skipped = [], []
    lens_count: dict = {}
    pillar_seen: set = set()

    # stable order: as returned by the agent
    for s in seeds:
        if s.get("lens") == "coverage-guard":
            skipped.append((s, "coverage-guard note, not an idea"))
            continue
        _id, kind = library.find_matching_idea(s["working_title"], s["premise"])
        if kind == "exact":
            skipped.append((s, f"already in backlog ({_id})"))
            continue
        selected.append(s)

    # diversify: first pass respects per-lens cap and one-per-pillar; then fill.
    diversified, overflow = [], []
    for s in selected:
        lens = s.get("lens", "")
        pillar = s.get("primary_pillar", "")
        if lens_count.get(lens, 0) < per_lens_cap and pillar not in pillar_seen:
            diversified.append(s)
            lens_count[lens] = lens_count.get(lens, 0) + 1
            if pillar:
                pillar_seen.add(pillar)
        else:
            overflow.append(s)
    picked = (diversified + overflow)[:max_n]
    for s in (diversified + overflow)[max_n:]:
        skipped.append((s, "beyond max_n for this run"))
    return picked, skipped


# --- into the backlog + briefs ---------------------------------------------

def seeds_to_backlog(selected: list, library: EditorialLibrary, *, today=None) -> list:
    """Add selected seeds to the one backlog through the existing dedup machinery.
    Returns list of (idea_id, seed)."""
    today = today or date.today().isoformat()
    pairs = []
    for s in selected:
        match_id, kind = library.find_matching_idea(s["working_title"], s["premise"])
        if kind == "exact":
            continue
        evidence = "; ".join(f"{e.get('source', '')}:{e.get('ref', '')}"
                             for e in s.get("evidence", []))[:240]
        fields = {
            "source_type": "discover",
            "source_ref": f"lens:{s.get('lens', '')}",
            "status": "proposed",
            "primary_pillar": s.get("primary_pillar", ""),
            "secondary_pillar": s.get("secondary_pillar", ""),
            "intended_format": s.get("suggested_format", ""),
            "intended_channel": s.get("suggested_channel", ""),
            "timeliness": s.get("timeliness", ""),
            "related_work": evidence,
            "chain_opportunity": (s.get("rationale", "") or "")[:200],
        }
        if kind == "near":
            fields["related_idea_ids"] = match_id
        idea_id = library.add_idea(s["working_title"], s["premise"], today=today, **fields)
        pairs.append((idea_id, s))
    return pairs


_DEFAULT_LENGTHS = {"short_form": 150, "long_form": 900,
                                        "companion_post": 150}


def develop_briefs(pairs: list, *, default_channel="neutral", default_format="short_form",
                   audience="") -> list:
    """Assemble briefs from selected (idea_id, seed) pairs. Deterministic packaging: the
    creative fields already came from the seed; this fills the output spec."""
    briefs = []
    for idea_id, s in pairs:
        fmt = s.get("suggested_format") or default_format
        briefs.append({
            "idea_id": idea_id,
            "working_title": s["working_title"],
            "premise": s["premise"],
            "format": fmt,
            "channel": s.get("suggested_channel") or default_channel,
            "target_length": _DEFAULT_LENGTHS.get(fmt, 300),
            "audience": audience,
            "relationship": "standalone",
            "link_strategy": "",
            "call_to_action": "",
            "primary_pillar": s.get("primary_pillar", ""),
            "secondary_pillar": s.get("secondary_pillar", ""),
            "why_chosen": {
                "lens": s.get("lens", ""),
                "evidence": s.get("evidence", []),
                "why_now": s.get("rationale", ""),
            },
        })
    return briefs


def write_briefs(config: dict, briefs: list, *, run_id: str) -> str:
    out = Path(config["workspace_dir"]) / run_id / "briefs.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(briefs, indent=2), encoding="utf-8")
    return str(out)
