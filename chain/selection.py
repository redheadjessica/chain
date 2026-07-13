#!/usr/bin/env python3
"""Selection traceability — a durable, append-only record of WHY an idea moved into
production, not just that it did.

If CHAIN (or a human, or an agent acting on the user's behalf) picks one idea from
several to develop, that choice must be reconstructable later: which candidates were
considered, which was picked, whether the pick was automatic or user-directed, what
factors mattered, and whether it was a true quality ranking, a diversification move,
or a manual/ad hoc call. Nothing here re-ranks anything — this module only records
what already happened.

Deliberately NOT a new review queue or UI: one flat, append-only JSONL file under
chain_home/state/, the same durability pattern as the ingest ledger and intake
manifest. `produce.run_production` reads the caller-supplied `selection` dict and
surfaces it in the packet; this module is how that dict gets logged and looked up.

Stdlib only.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

RANKING_TYPES = {"quality", "diversification", "manual", "none-recorded"}
MECHANISMS = {"automatic", "user-directed", "manual-test"}


def log_path(config: dict) -> Path:
    return Path(config["chain_home"]) / "state" / "selection-log.jsonl"


def record_selection(config: dict, *, selected_idea_id: str, candidates: list,
                     mechanism: str, factors: str = "", ranking_type: str = "none-recorded",
                     note: str = "", today=None) -> dict:
    """Append one selection event. `candidates` is the list of idea_ids that were
    available/considered (selected_idea_id should be among them). Returns the
    written record."""
    if mechanism not in MECHANISMS:
        raise ValueError(f"mechanism must be one of {sorted(MECHANISMS)}, got {mechanism!r}")
    if ranking_type not in RANKING_TYPES:
        raise ValueError(f"ranking_type must be one of {sorted(RANKING_TYPES)}, got {ranking_type!r}")
    record = {
        "date": today or date.today().isoformat(),
        "selected_idea_id": selected_idea_id,
        "candidates": list(candidates),
        "mechanism": mechanism,
        "ranking_type": ranking_type,
        "factors": factors,
        "note": note,
    }
    p = log_path(config)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return record


def load_selection_log(config: dict) -> list:
    p = log_path(config)
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def latest_selection_for(config: dict, idea_id: str) -> dict | None:
    """Most recent logged selection event that picked this idea, or None if the
    idea's selection was never recorded — callers must report that honestly rather
    than inventing a retrospective ranking."""
    matches = [r for r in load_selection_log(config) if r["selected_idea_id"] == idea_id]
    return matches[-1] if matches else None


def as_packet_selection(record: dict | None) -> dict:
    """Shape a selection-log record into the {mechanism, note} dict run_production's
    packet builder expects. None -> an honest 'not recorded' note."""
    if record is None:
        return {"mechanism": "not recorded",
                "note": "no selection event was logged for this idea"}
    mech = {"automatic": "selected automatically by CHAIN",
           "user-directed": "selected by the user",
           "manual-test": "selected manually (test/validation run)"}[record["mechanism"]]
    ranking = {"quality": "a true quality ranking", "diversification": "a diversification choice",
              "manual": "a manual, ad hoc choice", "none-recorded": "no ranking was recorded"}[record["ranking_type"]]
    note = f"{ranking}. Factors: {record['factors'] or '(none recorded)'}."
    if record.get("note"):
        note += f" {record['note']}"
    return {"mechanism": mech, "note": note}
