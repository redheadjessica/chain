#!/usr/bin/env python3
"""Idempotent source intake + idea harvesting.

Turns configured sources into ideas in the ONE backlog, without repeating work or
duplicating ideas. The engine is fully deterministic (no model) — the token-aware part
of intake is the optional, separate proposer for assisted/deep mapping.

Idempotency has two layers:
  * The ingestion ledger (chain_home/state/ingest-ledger.csv) records each file's
    content hash. Unchanged files are skipped with zero work — so unchanged sources
    never re-emit ideas.
  * Idea dedup (EditorialLibrary.find_matching_idea) prevents EXACT duplicate ideas and
    flags NEAR duplicates without blocking, covering the case where a changed file
    still contains ideas already in the backlog.

Harvested ideas enter the single backlog automatically with status `proposed`.

Stdlib only.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .editorial_library import EditorialLibrary, join_multi
from .sources import Source, harvest_ideas, index_source

LEDGER_FIELDS = ["source", "rel_path", "sha256", "size", "last_ingested", "kind",
                 "ideas_emitted", "note"]


class IngestLedger:
    """Durable record of what has been ingested, keyed by (source, rel_path)."""

    def __init__(self, path):
        self.path = Path(path)
        self.rows: list[dict] = []
        if self.path.exists():
            with self.path.open(newline="", encoding="utf-8") as fh:
                self.rows = list(csv.DictReader(fh))
        self._index = {(r["source"], r["rel_path"]): r for r in self.rows}

    @classmethod
    def open(cls, chain_home):
        return cls(Path(chain_home) / "state" / "ingest-ledger.csv")

    def get(self, source: str, rel_path: str):
        return self._index.get((source, rel_path))

    def upsert(self, source, rel_path, sha256, size, when, kind, ideas_emitted, note=""):
        row = self._index.get((source, rel_path))
        if row is None:
            row = {"source": source, "rel_path": rel_path}
            self.rows.append(row)
            self._index[(source, rel_path)] = row
        row.update({
            "sha256": sha256, "size": str(size), "last_ingested": when,
            "kind": kind, "ideas_emitted": join_multi(ideas_emitted), "note": note,
        })

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=LEDGER_FIELDS, extrasaction="ignore")
            w.writeheader()
            for r in self.rows:
                w.writerow({f: r.get(f, "") for f in LEDGER_FIELDS})


@dataclass
class IngestSummary:
    files_seen: int = 0
    unchanged: int = 0
    new_or_changed: int = 0
    ideas_added: int = 0
    exact_dupes_skipped: int = 0
    near_dupes_flagged: int = 0
    added_idea_ids: list = field(default_factory=list)
    flagged: list = field(default_factory=list)      # (idea_id, near_of)
    missing_sources: list = field(default_factory=list)

    def as_text(self) -> str:
        lines = [
            f"files seen:        {self.files_seen}",
            f"  unchanged:       {self.unchanged}  (skipped, zero cost)",
            f"  new/changed:     {self.new_or_changed}",
            f"ideas added:       {self.ideas_added}  {self.added_idea_ids}",
            f"exact dupes:       {self.exact_dupes_skipped}  (prevented)",
            f"near dupes:        {self.near_dupes_flagged}  (flagged, not blocked)",
        ]
        if self.missing_sources:
            lines.append(f"missing sources:   {self.missing_sources}")
        return "\n".join(lines)


def run_ingest(config: dict, *, today=None) -> IngestSummary:
    """Ingest all enabled sources into the library backlog. Requires config keys
    `chain_home`, `library_dir`, and `sources`. Deterministic and idempotent."""
    today = today or date.today().isoformat()
    library = EditorialLibrary.open(config["library_dir"])
    ledger = IngestLedger.open(config["chain_home"])
    summary = IngestSummary()

    for sd in config.get("sources", []):
        source = Source.from_dict(sd)
        if not source.enabled:
            continue
        if not Path(source.path).exists():
            summary.missing_sources.append(source.name)
            continue

        for idx in index_source(source):
            summary.files_seen += 1
            prev = ledger.get(source.name, idx.rel_path)
            if prev and prev.get("sha256") == idx.sha256:
                summary.unchanged += 1
                continue  # unchanged file: no work, no re-emitted ideas

            emitted = []
            if source.idea_marker:   # harvest marked ideas from ANY source, generically
                try:
                    text = Path(idx.path).read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    text = ""
                for title, premise in harvest_ideas(text, source.idea_marker):
                    match_id, kind = library.find_matching_idea(title, premise)
                    if kind == "exact":
                        summary.exact_dupes_skipped += 1
                        continue
                    fields = {
                        # generic origin + role, no domain assumption:
                        "source_type": f"harvest:{source.primary_role}",
                        "source_ref": f"{source.name}:{idx.rel_path}",
                        "status": "proposed",
                        "intended_channel": "neutral",
                    }
                    if kind == "near":
                        fields["related_idea_ids"] = match_id
                        fields["chain_opportunity"] = f"near-duplicate of {match_id} (review)"
                    idea_id = library.add_idea(title, premise, today=today, **fields)
                    emitted.append(idea_id)
                    summary.ideas_added += 1
                    summary.added_idea_ids.append(idea_id)
                    if kind == "near":
                        summary.near_dupes_flagged += 1
                        summary.flagged.append((idea_id, match_id))

            kind_label = "idea-harvest" if source.idea_marker else "corpus"
            ledger.upsert(source.name, idx.rel_path, idx.sha256, idx.size,
                          today, kind_label, emitted)
            summary.new_or_changed += 1

    library.save()
    ledger.save()
    return summary


def main(argv=None):
    import argparse
    from .config import load_config
    ap = argparse.ArgumentParser(description="CHAIN source intake + idea harvesting")
    ap.add_argument("config", nargs="?", help="path to a config yaml (default: local)")
    args = ap.parse_args(argv)
    cfg = load_config(local_path=args.config) if args.config else load_config()
    summary = run_ingest(cfg)
    print(summary.as_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
