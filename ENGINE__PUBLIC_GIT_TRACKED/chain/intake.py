#!/usr/bin/env python3
"""Adaptive editorial intake — the deterministic core.

CHAIN must be able to onboard a user at ANY level of editorial maturity without
requiring them to have already done the work CHAIN exists to help them do. For every
major editorial input there are three states, all first-class:

  exists   -> reference and validate it where it already lives (map in place)
  partial  -> assess, improve, and fill gaps
  missing  -> create a first version collaboratively

This module is the zero-token half of that experience: an asset registry, an
inspector that classifies each asset from what is actually on disk, a computed
user-maturity level, a plan generator (smallest useful next step per gap), and a
durable manifest (chain_home/state/intake-manifest.json) so later runs never repeat
finished work. The conversational half — locating scattered material, interviews,
writing exercises, distilling guidance from raw material — is the portable
`chain-intake` agent (.claude/agents/chain-intake.md), which runs THIS module first
and works from its report.

Privacy: everything user-specific lands in chain_home or in files the user already
keeps. Nothing here writes inside the repo. Stdlib only.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .discover import parse_pillars
from .sources import Source, walk_source

MANIFEST_VERSION = 1

# Content thresholds: below `min_words` a present file is "partial", not "exists".
# Deliberately low — intake accepts a genuinely small-but-real asset ("smallest
# useful version"), it only refuses to count stubs and untouched templates.
_TEMPLATE_ECHO = re.compile(r"^#[^\n]*\(template\)|> Replace|Replace the placeholders",
                            re.IGNORECASE | re.MULTILINE)

CORPUS_ROLES = {"published", "samples"}
CORPUS_FULL = 8          # >= this many corpus docs -> exists
DRAFT_ROLES = {"drafts"}


@dataclass(frozen=True)
class Asset:
    key: str
    label: str
    tier: str                 # "required" | "recommended" | "optional"
    purpose: str               # what it is FOR — shown when it's missing
    first_step: str            # the smallest useful next step when absent
    kind: str = "file"         # "file" | "config-sources" | "corpus" | "corpus-drafts"
    config_key: str = ""       # config key that may already point at it
    default_file: str = ""     # default location under chain_home when created
    template: str = ""         # repo-relative starter template
    min_words: int = 40
    validator: str = ""        # extra check: "pillars"


REGISTRY: tuple = (
    Asset("source_map", "Source map", "required",
          "Where your existing material lives and what kind of signal each source carries. "
          "Everything else reads through it.",
          "Name the folders you already have (or want) and what's in each; CHAIN maps them "
          "in place — nothing is moved.",
          kind="config-sources"),
    Asset("corpus", "Representative writing", "required",
          "Real examples of you at your best — published work or honest samples. Voice is "
          "learned from evidence, not adjectives.",
          "Point at anything you've published. Starting from nothing? Two or three short "
          "writing exercises produce enough signal to begin.",
          kind="corpus"),
    Asset("voice_spec", "Voice & style guidance", "required",
          "What you sound like, written for an agent: register, rhythm, hard rules, "
          "what editing must never remove.",
          "If a style guide exists anywhere, point at it. Otherwise a 20-minute interview "
          "plus your samples produces a usable first version.",
          config_key="voice_spec", default_file="voice-spec.md",
          template="canon/voice-spec.template.md", min_words=120),
    Asset("positioning", "Positioning / reputation signals", "required",
          "What readers should gradually come to believe about you. The evaluator scores "
          "every piece against these, above engagement.",
          "Answer one question — 'after six months of reading you, what should someone "
          "believe about you?' — and turn the answers into 3-6 pillars.",
          config_key="positioning_pillars", default_file="positioning-pillars.md",
          template="canon/positioning-pillars.template.md", min_words=30,
          validator="pillars"),
    Asset("themes", "Editorial themes", "recommended",
          "The territories ideas are drawn from — sources of ideas, not quotas.",
          "List the subjects you actually think and talk about; rough is fine, it evolves.",
          default_file="editorial-themes.md",
          template="canon/editorial-themes.template.md", min_words=30),
    Asset("anti_patterns", "Anti-patterns / hard no's", "recommended",
          "The moves that must never appear in your name — phrases, structures, tones. "
          "Cheap to write, prevents the worst failure mode.",
          "Name the writing that makes you cringe; even five bullets is a real start.",
          default_file="anti-patterns.md",
          template="canon/anti-patterns.template.md", min_words=30),
    Asset("audience_outcomes", "Audience & desired outcomes", "recommended",
          "Who the writing is for and what it should cause — readers helped, and what "
          "public writing should do for YOU.",
          "One paragraph on who reads you (or should), one on what a great year of "
          "publishing would change.",
          default_file="audience-and-outcomes.md",
          template="canon/audience-and-outcomes.template.md", min_words=30),
    Asset("drafts", "Drafts / unfinished material", "optional",
          "Unpublished starts and fragments — a rich idea source when present.",
          "If half-written things exist, map their folder with role `drafts`.",
          kind="corpus-drafts"),
    Asset("principles", "Editorial principles / decision framework", "optional",
          "Tie-breakers for editorial judgment calls (e.g. 'interesting beats impressive').",
          "Write the 3-5 rules you'd give a smart editor acting on your behalf.",
          default_file="editorial-principles.md",
          template="canon/editorial-principles.template.md", min_words=30),
    Asset("story_bank", "Story / anecdote bank", "optional",
          "Reusable true stories with their facts pinned — so agents never embellish.",
          "Capture 3-5 stories you already tell out loud, each with its real details.",
          default_file="story-bank.md",
          template="canon/story-bank.template.md", min_words=40),
    Asset("exemplar_index", "Exemplar index", "optional",
          "The handful of pieces that best exemplify your voice, annotated with WHY — "
          "imitation targets, stronger than any description.",
          "Pick 3-8 favorites from your corpus and write one line each on what they prove.",
          default_file="exemplar-index.md",
          template="canon/exemplar-index.template.md", min_words=30),
    Asset("feedback_ledger", "Feedback ledger", "optional",
          "Where your reactions to drafts accumulate into durable rules. Newest entries "
          "outrank every spec.",
          "Create the empty ledger; it earns its value the first time you react to a draft.",
          default_file="feedback-ledger.md",
          template="canon/feedback-ledger.template.md", min_words=10),
    Asset("channel_guidance", "Channel-specific guidance", "optional",
          "Per-channel overlays (length norms, formatting, register shifts). Generic packs "
          "ship in canon/channels/; this is your personal layer.",
          "Only worth writing once a channel's defaults chafe; skip until then.",
          default_file="channel-guidance.md", min_words=30),
)

ASSETS = {a.key: a for a in REGISTRY}


# --- classification ----------------------------------------------------------

def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9''\-]+", text))


def _classify_file(asset: Asset, path_str: str) -> dict:
    if not path_str:
        return {"status": "missing", "path": "", "detail": "no location configured"}
    p = Path(path_str).expanduser()
    if not p.exists():
        return {"status": "missing", "path": str(p), "detail": f"not found: {p}"}
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return {"status": "partial", "path": str(p), "detail": f"unreadable: {exc}"}
    if _TEMPLATE_ECHO.search(text):
        return {"status": "partial", "path": str(p),
                "detail": "still contains template placeholders"}
    if asset.validator == "pillars":
        n = len(parse_pillars(p))
        if n == 0:
            return {"status": "partial", "path": str(p),
                    "detail": "no parseable `| id | label |` pillar rows"}
        return {"status": "exists", "path": str(p), "detail": f"{n} pillar(s)"}
    words = _word_count(text)
    if words < asset.min_words:
        return {"status": "partial", "path": str(p),
                "detail": f"only ~{words} words (threshold {asset.min_words})"}
    return {"status": "exists", "path": str(p), "detail": f"~{words} words"}


def _source_stats(config: dict) -> list:
    out = []
    for sd in config.get("sources", []):
        source = Source.from_dict(sd)
        n = 0
        if source.enabled and Path(source.path).exists():
            n = sum(1 for _ in walk_source(source))
        out.append({"name": source.name, "path": source.path,
                    "roles": list(source.roles), "enabled": source.enabled, "files": n})
    return out


def _resolve_path(asset: Asset, config: dict, manifest: dict) -> str:
    recorded = (manifest.get("assets", {}).get(asset.key, {}) or {}).get("path", "")
    if recorded:
        return recorded
    if asset.config_key:
        v = str(config.get(asset.config_key) or "")
        if v:
            return v
    if asset.default_file:
        return str(Path(config["chain_home"]) / asset.default_file)
    return ""


def classify(config: dict, manifest: dict | None = None) -> tuple:
    """Return (classifications, source_stats). classifications: {key: {status, path,
    detail}}. Pure inspection — no writes."""
    manifest = manifest or {}
    stats = _source_stats(config)
    live = [s for s in stats if s["enabled"] and s["files"] > 0]
    cls: dict = {}

    for asset in REGISTRY:
        if asset.kind == "config-sources":
            if not [s for s in stats if s["enabled"]]:
                cls[asset.key] = {"status": "missing", "path": "",
                                  "detail": "no sources configured"}
            elif not live:
                cls[asset.key] = {"status": "partial", "path": "",
                                  "detail": "sources configured but none yield any files"}
            else:
                cls[asset.key] = {"status": "exists", "path": "",
                                  "detail": f"{len(live)} live source(s), "
                                            f"{sum(s['files'] for s in live)} file(s)"}
        elif asset.kind in ("corpus", "corpus-drafts"):
            roles = CORPUS_ROLES if asset.kind == "corpus" else DRAFT_ROLES
            n = sum(s["files"] for s in live if roles & set(s["roles"]))
            if n == 0:
                cls[asset.key] = {"status": "missing", "path": "",
                                  "detail": f"no files in sources with roles {sorted(roles)}"}
            elif asset.kind == "corpus" and n < CORPUS_FULL:
                cls[asset.key] = {"status": "partial", "path": "",
                                  "detail": f"{n} doc(s) — usable, thin (target {CORPUS_FULL}+)"}
            else:
                cls[asset.key] = {"status": "exists", "path": "", "detail": f"{n} doc(s)"}
        else:
            cls[asset.key] = _classify_file(asset, _resolve_path(asset, config, manifest))
    return cls, stats


LEVEL3_MAX_FILES = 4   # <= this many raw files total still counts as "almost nothing"


def maturity_level(cls: dict, stats: list) -> int:
    """1 = organized (map & validate) · 2 = raw material, no system (classify & distill)
    · 3 = starting from almost nothing (create collaboratively). Computed, never asked."""
    sources_ok = cls["source_map"]["status"] == "exists"
    corpus = cls["corpus"]["status"]
    voice = cls["voice_spec"]["status"]
    live_files = sum(s["files"] for s in stats if s["enabled"])
    if corpus == "missing" and voice == "missing" and live_files <= LEVEL3_MAX_FILES:
        return 3
    if sources_ok and corpus == "exists" and voice in ("exists", "partial"):
        return 1
    return 2

MATURITY_LABELS = {1: "already organized — map, validate, fill gaps",
                   2: "has raw material — classify, distill, create what's missing",
                   3: "starting fresh — create a usable starting point together"}


# --- plan --------------------------------------------------------------------

_ACTIONS = {"missing": "locate-or-create", "partial": "improve"}


def build_plan(cls: dict, manifest: dict | None = None) -> list:
    """Smallest useful next step per gap, blockers first. Skipped optional assets are
    honored. Never proposes recreating something that exists."""
    manifest = manifest or {}
    plan = []
    for asset in REGISTRY:
        c = cls[asset.key]
        rec = (manifest.get("assets", {}) or {}).get(asset.key, {}) or {}
        if c["status"] == "exists" or rec.get("skipped"):
            continue
        step = asset.first_step
        if asset.key == "corpus" and c["status"] == "partial":
            step = (f"Usable but thin ({c['detail']}) — map or write a few more "
                    f"representative pieces.")
        plan.append({
            "asset": asset.key, "label": asset.label, "tier": asset.tier,
            "status": c["status"], "action": _ACTIONS[c["status"]],
            "why": asset.purpose, "step": step,
            "detail": c["detail"], "template": asset.template,
            # partial = usable-but-thin; only a genuinely absent required asset blocks
            "blocking": asset.tier == "required" and c["status"] == "missing",
        })
    order = {"required": 0, "recommended": 1, "optional": 2}
    plan.sort(key=lambda s: order[s["tier"]])
    return plan


# --- manifest ----------------------------------------------------------------

def manifest_path(config: dict) -> Path:
    return Path(config["chain_home"]) / "state" / "intake-manifest.json"


def load_manifest(config: dict) -> dict:
    p = manifest_path(config)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def build_manifest(config: dict, *, today: str | None = None) -> dict:
    """Inspect + merge with any prior manifest. Recomputes every status from disk;
    preserves human-set fields (provenance, last_reviewed, skipped, notes, paths).
    Stores locations and statuses only — never source content."""
    today = today or date.today().isoformat()
    prev = load_manifest(config)
    cls, stats = classify(config, prev)
    prev_assets = prev.get("assets", {}) or {}

    assets = {}
    for asset in REGISTRY:
        c = cls[asset.key]
        old = prev_assets.get(asset.key, {}) or {}
        assets[asset.key] = {
            "label": asset.label, "tier": asset.tier,
            "status": c["status"], "path": c["path"] or old.get("path", ""),
            "detail": c["detail"],
            "provenance": old.get("provenance", ""),   # user-provided|improved|created
            "last_reviewed": old.get("last_reviewed", ""),
            "skipped": bool(old.get("skipped", False)),
            "notes": old.get("notes", ""),
        }

    manifest = {
        "version": MANIFEST_VERSION,
        "created": prev.get("created", today),
        "updated": today,
        "maturity_level": maturity_level(cls, stats),
        "sources": stats,
        "assets": assets,
        "blockers": [a.key for a in REGISTRY
                     if a.tier == "required" and cls[a.key]["status"] == "missing"],
    }
    return manifest


def save_manifest(config: dict, manifest: dict) -> Path:
    p = manifest_path(config)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return p


# --- the one progress summary -------------------------------------------------

def summary(manifest: dict, plan: list) -> str:
    a = manifest["assets"]

    def keys(pred):
        return [v["label"] for k, v in a.items() if pred(k, v)]

    found = keys(lambda k, v: v["status"] == "exists" and v["provenance"] in ("", "user-provided"))
    created = keys(lambda k, v: v["provenance"] == "created" and v["status"] != "missing")
    improved = keys(lambda k, v: v["provenance"] == "improved" and v["status"] != "missing")
    skipped = keys(lambda k, v: v["skipped"])
    blocking = [s for s in plan if s["blocking"]]
    strengthen = [s for s in plan if s["tier"] == "required" and not s["blocking"]]
    optional_open = [s for s in plan if s["tier"] == "optional"]
    recommended_open = [s for s in plan if s["tier"] == "recommended"]

    lines = [f"CHAIN intake — maturity level {manifest['maturity_level']} "
             f"({MATURITY_LABELS[manifest['maturity_level']]})", ""]

    def section(title, items):
        if items:
            lines.append(title)
            lines.extend(f"  - {i}" for i in items)

    section("Found and accepted as-is:", found)
    section("Created together:", created)
    section("Improved:", improved)
    section("Deliberately skipped:", skipped)
    if blocking:
        lines.append("Blocks writing quality (do these first):")
        for s in blocking:
            lines.append(f"  - {s['label']} [{s['status']}] — {s['step']}")
    if strengthen:
        lines.append("In place, worth strengthening over time:")
        for s in strengthen:
            lines.append(f"  - {s['label']} — {s['step']}")
    if recommended_open:
        lines.append("Recommended next:")
        for s in recommended_open:
            lines.append(f"  - {s['label']} [{s['status']}] — {s['step']}")
    if optional_open:
        lines.append("Optional (fine to skip):")
        lines.extend(f"  - {s['label']}" for s in optional_open)
    if not blocking:
        lines.append("")
        lines.append("No blockers — CHAIN has enough to write with.")
    return "\n".join(lines)


# --- CLI ----------------------------------------------------------------------

def _apply_marks(manifest: dict, args) -> None:
    def _pairs(items):
        for item in items or []:
            if "=" not in item:
                raise SystemExit(f"expected ASSET=VALUE, got: {item}")
            yield item.split("=", 1)

    for key, prov in _pairs(args.mark):
        if key not in ASSETS:
            raise SystemExit(f"unknown asset: {key} (known: {', '.join(ASSETS)})")
        if prov not in ("user-provided", "improved", "created"):
            raise SystemExit(f"provenance must be user-provided|improved|created, got {prov}")
        manifest["assets"][key]["provenance"] = prov
    for key, path in _pairs(args.set_path):
        if key not in ASSETS:
            raise SystemExit(f"unknown asset: {key}")
        manifest["assets"][key]["path"] = str(Path(path).expanduser())
    for key in args.skip or []:
        if key not in ASSETS:
            raise SystemExit(f"unknown asset: {key}")
        if ASSETS[key].tier == "required":
            raise SystemExit(f"{key} is required and cannot be skipped")
        manifest["assets"][key]["skipped"] = True
    for key in args.unskip or []:
        manifest["assets"][key]["skipped"] = False
    for key, note in _pairs(args.note):
        if key not in ASSETS:
            raise SystemExit(f"unknown asset: {key}")
        manifest["assets"][key]["notes"] = note
    for key in args.reviewed or []:
        if key not in ASSETS:
            raise SystemExit(f"unknown asset: {key}")
        manifest["assets"][key]["last_reviewed"] = manifest["updated"]


def main(argv=None):
    import argparse
    from .config import load_config
    ap = argparse.ArgumentParser(
        description="CHAIN adaptive intake — inspect, classify, plan (zero tokens)")
    ap.add_argument("config", nargs="?", help="path to a config yaml (default: local)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--mark", action="append", metavar="ASSET=PROVENANCE",
                    help="record provenance: user-provided|improved|created")
    ap.add_argument("--set-path", action="append", metavar="ASSET=PATH",
                    help="map an asset to a file that already exists (in place)")
    ap.add_argument("--skip", action="append", metavar="ASSET",
                    help="mark an optional asset as deliberately skipped")
    ap.add_argument("--unskip", action="append", metavar="ASSET")
    ap.add_argument("--note", action="append", metavar="ASSET=TEXT",
                    help="attach a durable note (e.g. a recommendation) to an asset")
    ap.add_argument("--reviewed", action="append", metavar="ASSET",
                    help="stamp last_reviewed = today")
    args = ap.parse_args(argv)

    cfg = load_config(local_path=args.config) if args.config else load_config()
    manifest = build_manifest(cfg)
    _apply_marks(manifest, args)
    if args.set_path:
        # re-inspect so newly mapped paths classify immediately
        save_manifest(cfg, manifest)
        manifest = build_manifest(cfg)
        _apply_marks(manifest, args)
    save_manifest(cfg, manifest)
    cls, _ = classify(cfg, manifest)
    plan = build_plan(cls, manifest)

    if args.json:
        print(json.dumps({"manifest": manifest, "plan": plan}, indent=2))
    else:
        print(summary(manifest, plan))
        print(f"\nmanifest: {manifest_path(cfg)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
