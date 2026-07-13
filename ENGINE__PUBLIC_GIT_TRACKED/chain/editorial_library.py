#!/usr/bin/env python3
"""The editorial library — the smallest durable store CHAIN needs.

Two flat CSVs joined by stable IDs, living under `chain_home/library/`:

  * ideas.csv  — the persistent core object. One idea, many pieces.
  * pieces.csv — one row per piece of writing. A piece's status moves
                 draft -> published; "drafts" and "published" are views of the SAME
                 rows by status, not separate stores.

Design rules this module enforces (from the approved architecture):
  * A relationship is stored ONCE. The pieces belonging to an idea are DERIVED by
    filtering pieces.csv on idea_id — there is no piece_ids column on the idea.
  * Cross-links (related ideas / related pieces) use "|", never a comma, so free
    text stays CSV-safe.
  * The index REFERENCES where a piece lives (url / final_text_path); it is not a
    second canonical copy of your writing (single source of truth).
  * Manual idea entry is lightweight: a working_title + premise is a valid idea.
  * No engagement/analytics column here. Metrics are V2 and will live in a separate,
    time-stamped history file, not one cell.

Stdlib only. Agents mutate the library ONLY through this helper so hand-editing
never corrupts the CSV; humans edit the spreadsheet directly between runs, and
groom() reconciles anything they added by hand.
"""

from __future__ import annotations

import csv
import difflib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# --- schema -----------------------------------------------------------------

IDEA_ID_RE = re.compile(r"^IDEA-(\d{4,})$")
PIECE_ID_RE = re.compile(r"^PIECE-(\d{4,})$")
MULTIVALUE_DELIM = "|"

# Canonical column order. Note: NO piece_ids on the idea (derived), NO analytics on
# the piece (V2, separate file).
IDEAS_FIELDS = [
    "idea_id",
    "working_title",
    "premise",
    "status",
    "source_type",
    "source_ref",
    "date_added",
    "last_touched",
    "intended_format",
    "intended_channel",
    "primary_pillar",
    "secondary_pillar",
    "user_interest",
    "user_feedback",
    "chain_opportunity",
    "timeliness",
    "expires",
    "related_work",
    "related_idea_ids",   # "|"-delimited IDEA-ids
    "rejected_reason",
]

PIECES_FIELDS = [
    "piece_id",
    "idea_id",            # originating idea (the single stored direction)
    "title_or_opening",
    "format",
    "channel",
    "status",             # draft | published | parked
    "pub_date",
    "url",                # where it lives once published (reference, not a copy)
    "final_text_path",    # review-root draft path or your canonical file (reference, not a copy)
    "parent_piece_id",    # e.g. the long-form piece a companion belongs to
    "related_piece_ids",  # "|"-delimited PIECE-ids
    "relation_type",      # companion-of | expands | condenses | promotes | follows-up
    "pillar",
    "notes",
]

IDEA_STATUSES = {
    "proposed", "developing", "briefed", "in-production",
    "produced", "published", "parked", "rejected",
}
# A Piece moves draft -> final -> published (or parked). User-facing, "draft" and
# "final" are both "Drafts" (unpublished); only "published" is "Published writing".
PIECE_STATUSES = {"draft", "final", "published", "parked"}
UNPUBLISHED_PIECE_STATUSES = {"draft", "final"}

# Ideas hidden from the normal active view (rejected/parked are preserved, not shown).
INACTIVE_IDEA_STATUSES = {"rejected", "parked"}

# The only fields a human must supply to add an idea by hand.
IDEA_MINIMAL_REQUIRED = ("working_title", "premise")

# Near-duplicate threshold for idea dedup (difflib ratio on normalized premise).
NEAR_DUPLICATE_RATIO = 0.85


def normalize_text(s: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace — for duplicate detection."""
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# --- problems ---------------------------------------------------------------

@dataclass(frozen=True)
class Problem:
    severity: str   # "error" | "warn"
    code: str
    row_id: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.code} ({self.row_id or '-'}): {self.message}"


# --- helpers ----------------------------------------------------------------

def split_multi(value: str) -> list[str]:
    """Parse a '|'-delimited multi-value cell into a clean list."""
    if not value:
        return []
    return [v.strip() for v in value.split(MULTIVALUE_DELIM) if v.strip()]


def join_multi(values) -> str:
    return MULTIVALUE_DELIM.join(v.strip() for v in values if str(v).strip())


def _read_csv(path: Path, fields: list[str]) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:  # ensure every declared field exists on every row
        for f in fields:
            r.setdefault(f, "")
    return rows


def _write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({f: r.get(f, "") for f in fields})


def _next_id(existing_ids, regex, prefix: str, width: int = 4) -> str:
    hi = 0
    for cid in existing_ids:
        m = regex.match(cid or "")
        if m:
            hi = max(hi, int(m.group(1)))
    return f"{prefix}-{hi + 1:0{width}d}"


# --- the library ------------------------------------------------------------

class EditorialLibrary:
    """Load, mutate, validate the two CSVs. Owns all ID minting."""

    def __init__(self, ideas_path, pieces_path):
        self.ideas_path = Path(ideas_path)
        self.pieces_path = Path(pieces_path)
        self.ideas: list[dict] = _read_csv(self.ideas_path, IDEAS_FIELDS)
        self.pieces: list[dict] = _read_csv(self.pieces_path, PIECES_FIELDS)

    @classmethod
    def open(cls, library_dir):
        d = Path(library_dir)
        return cls(d / "ideas.csv", d / "pieces.csv")

    # -- id minting --
    def mint_idea_id(self) -> str:
        return _next_id((r.get("idea_id", "") for r in self.ideas), IDEA_ID_RE, "IDEA")

    def mint_piece_id(self) -> str:
        return _next_id((r.get("piece_id", "") for r in self.pieces), PIECE_ID_RE, "PIECE")

    # -- derived relationship (stored once) --
    def pieces_for_idea(self, idea_id: str) -> list[dict]:
        """The pieces of an idea are DERIVED, never stored on the idea."""
        return [p for p in self.pieces if p.get("idea_id") == idea_id]

    def drafts(self) -> list[dict]:
        """Unpublished pieces (draft or final) — user-facing 'Drafts'."""
        return [p for p in self.pieces if p.get("status") in UNPUBLISHED_PIECE_STATUSES]

    def published(self) -> list[dict]:
        """User-facing 'Published writing'."""
        return [p for p in self.pieces if p.get("status") == "published"]

    def active_ideas(self) -> list[dict]:
        """The normal backlog view — rejected/parked are preserved but hidden."""
        return [r for r in self.ideas if r.get("status") not in INACTIVE_IDEA_STATUSES]

    # -- duplicate detection (deterministic; no model) --
    def find_matching_idea(self, working_title: str, premise: str,
                           *, threshold: float = NEAR_DUPLICATE_RATIO):
        """Return (idea_id, kind) where kind is 'exact' | 'near' | None. Compares the
        normalized premise (falling back to title) against ALL ideas, including
        rejected/parked ones, so a rejected idea is never silently re-proposed."""
        n_prem = normalize_text(premise)
        n_title = normalize_text(working_title)
        best_id, best_ratio = None, 0.0
        for r in self.ideas:
            r_prem = normalize_text(r.get("premise", ""))
            r_title = normalize_text(r.get("working_title", ""))
            if n_prem and (n_prem == r_prem or (n_title and n_title == r_title)):
                return r.get("idea_id"), "exact"
            ratio = difflib.SequenceMatcher(None, n_prem, r_prem).ratio() if n_prem and r_prem else 0.0
            if ratio > best_ratio:
                best_id, best_ratio = r.get("idea_id"), ratio
        if best_id and best_ratio >= threshold:
            return best_id, "near"
        return None, None

    def get_idea(self, idea_id: str):
        return next((r for r in self.ideas if r.get("idea_id") == idea_id), None)

    def get_piece(self, piece_id: str):
        return next((p for p in self.pieces if p.get("piece_id") == piece_id), None)

    # -- lightweight add --
    def add_idea(self, working_title: str, premise: str, *, today=None, **fields) -> str:
        if not working_title.strip() or not premise.strip():
            raise ValueError("an idea needs at least a working_title and a premise")
        today = today or date.today().isoformat()
        idea_id = self.mint_idea_id()
        row = {f: "" for f in IDEAS_FIELDS}
        row.update({
            "idea_id": idea_id,
            "working_title": working_title.strip(),
            "premise": premise.strip(),
            "status": fields.pop("status", "proposed"),
            "date_added": fields.pop("date_added", today),
            "last_touched": fields.pop("last_touched", today),
        })
        for k, v in fields.items():
            if k in IDEAS_FIELDS:
                row[k] = v
        self.ideas.append(row)
        return idea_id

    def add_piece(self, idea_id: str, *, fmt: str, channel: str, **fields) -> str:
        if not self.get_idea(idea_id):
            raise ValueError(f"unknown idea_id {idea_id!r}")
        piece_id = self.mint_piece_id()
        row = {f: "" for f in PIECES_FIELDS}
        row.update({
            "piece_id": piece_id,
            "idea_id": idea_id,
            "format": fmt,
            "channel": channel,
            "status": fields.pop("status", "draft"),
        })
        for k, v in fields.items():
            if k in PIECES_FIELDS:
                row[k] = v
        self.pieces.append(row)
        return piece_id

    # -- groom: reconcile human-added rows --
    def groom(self, *, today=None) -> list[str]:
        """Assign IDs to rows a human added by hand, and fill safe defaults.
        Returns human-readable change descriptions."""
        today = today or date.today().isoformat()
        changes: list[str] = []
        for r in self.ideas:
            if not r.get("idea_id"):
                r["idea_id"] = self.mint_idea_id()
                changes.append(f"assigned {r['idea_id']} to '{r.get('working_title', '')[:40]}'")
            r["status"] = r.get("status") or "proposed"
            r["date_added"] = r.get("date_added") or today
            r["last_touched"] = r.get("last_touched") or today
        for p in self.pieces:
            if not p.get("piece_id"):
                p["piece_id"] = self.mint_piece_id()
                changes.append(f"assigned {p['piece_id']}")
            p["status"] = p.get("status") or "draft"
        return changes

    # -- validation (ID integrity + orphaned references) --
    def validate(self) -> list[Problem]:
        problems: list[Problem] = []
        idea_ids = [r.get("idea_id", "") for r in self.ideas]
        piece_ids = [p.get("piece_id", "") for p in self.pieces]
        idea_id_set = {i for i in idea_ids if i}
        piece_id_set = {p for p in piece_ids if p}

        def dupes(seq):
            seen, dup = set(), set()
            for x in seq:
                if x and x in seen:
                    dup.add(x)
                seen.add(x)
            return dup

        for d in dupes(idea_ids):
            problems.append(Problem("error", "duplicate-id", d, "idea_id appears more than once"))
        for d in dupes(piece_ids):
            problems.append(Problem("error", "duplicate-id", d, "piece_id appears more than once"))

        for r in self.ideas:
            iid = r.get("idea_id", "")
            if not iid:
                problems.append(Problem("error", "missing-id", "", f"idea '{r.get('working_title', '')[:40]}' has no id (run groom)"))
            elif not IDEA_ID_RE.match(iid):
                problems.append(Problem("error", "bad-id-format", iid, "idea_id must look like IDEA-0001"))
            if r.get("status") and r["status"] not in IDEA_STATUSES:
                problems.append(Problem("warn", "unknown-status", iid, f"status '{r['status']}' not recognized"))
            for rel in split_multi(r.get("related_idea_ids", "")):
                if rel == iid:
                    problems.append(Problem("warn", "self-reference", iid, "related_idea_ids references itself"))
                elif rel not in idea_id_set:
                    problems.append(Problem("error", "orphaned-reference", iid, f"related_idea_ids -> unknown {rel}"))

        for p in self.pieces:
            pid = p.get("piece_id", "")
            if not pid:
                problems.append(Problem("error", "missing-id", "", "a piece row has no id (run groom)"))
            elif not PIECE_ID_RE.match(pid):
                problems.append(Problem("error", "bad-id-format", pid, "piece_id must look like PIECE-0001"))
            oid = p.get("idea_id", "")
            if not oid:
                problems.append(Problem("error", "missing-idea-id", pid, "piece has no originating idea_id"))
            elif oid not in idea_id_set:
                problems.append(Problem("error", "orphaned-reference", pid, f"idea_id -> unknown {oid}"))
            if p.get("status") and p["status"] not in PIECE_STATUSES:
                problems.append(Problem("warn", "unknown-status", pid, f"status '{p['status']}' not recognized"))
            parent = p.get("parent_piece_id", "")
            if parent:
                if parent == pid:
                    problems.append(Problem("warn", "self-reference", pid, "parent_piece_id references itself"))
                elif parent not in piece_id_set:
                    problems.append(Problem("error", "orphaned-reference", pid, f"parent_piece_id -> unknown {parent}"))
            for rel in split_multi(p.get("related_piece_ids", "")):
                if rel == pid:
                    problems.append(Problem("warn", "self-reference", pid, "related_piece_ids references itself"))
                elif rel not in piece_id_set:
                    problems.append(Problem("error", "orphaned-reference", pid, f"related_piece_ids -> unknown {rel}"))

        return problems

    def is_valid(self) -> bool:
        return not any(p.severity == "error" for p in self.validate())

    # -- persistence --
    def save(self) -> None:
        _write_csv(self.ideas_path, IDEAS_FIELDS, self.ideas)
        _write_csv(self.pieces_path, PIECES_FIELDS, self.pieces)


def main(argv=None):
    """Tiny CLI: `python -m chain.editorial_library validate <library_dir>`."""
    import argparse
    ap = argparse.ArgumentParser(description="CHAIN editorial-library utilities")
    ap.add_argument("command", choices=["validate", "groom"])
    ap.add_argument("library_dir", help="folder containing ideas.csv and pieces.csv")
    args = ap.parse_args(argv)

    lib = EditorialLibrary.open(args.library_dir)
    if args.command == "groom":
        changes = lib.groom()
        lib.save()
        print(f"groom: {len(changes)} change(s)")
        for c in changes:
            print(f"  - {c}")
        return 0

    problems = lib.validate()
    errors = [p for p in problems if p.severity == "error"]
    for p in problems:
        print(p)
    print(f"=> {len(errors)} error(s), {len(problems) - len(errors)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
