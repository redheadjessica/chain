#!/usr/bin/env python3
"""The production spine: Brief -> Draft -> Evaluate -> bounded Finalize.

Deterministic harness; the two creative roles are portable LLM agents injected as
`writer_fn` and `evaluator_fn`. The harness runs the mechanical lint, enforces the ONE
bounded revision cycle, runs preservation-mode lint on the revision, and assembles a
private **draft packet** into chain_home/workspace. It writes nothing public and copies
no full source library — only the run's own draft, baseline, and packet.

Division of responsibilities is enforced here:
  * lint_draft = mechanical only (never quality judgment)
  * writer     = drafts / surgically revises; may decline a finding with a reason
  * evaluator  = scores + candid verdict; never rewrites

Baseline draft (`draft-v1.md`) and the brief are preserved so a later learning slice can
reconcile against the user's published version. No learning happens here.

Stdlib only.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .lint_draft import has_errors, lint_draft

VERDICTS = {
    "Strong candidate to publish",
    "Good candidate with one issue to review",
    "Interesting but somewhat exposed",
    "Strategically useful, but currently too generic",
    "Do not publish this version",
}


# --- validation of the injected agents' output ------------------------------

def validate_draft(out) -> dict:
    if not isinstance(out, dict) or not isinstance(out.get("draft_text"), str) or not out["draft_text"].strip():
        raise ValueError("writer draft output needs a non-empty 'draft_text'")
    out.setdefault("links_used", [])
    out.setdefault("open_questions", [])
    return out


def validate_revision(out) -> dict:
    if not isinstance(out, dict) or not isinstance(out.get("final_text"), str) or not out["final_text"].strip():
        raise ValueError("writer revision output needs a non-empty 'final_text'")
    out.setdefault("changes_applied", [])
    out.setdefault("declined", [])
    out.setdefault("open_questions", [])
    return out


def validate_evaluation(out) -> dict:
    for k in ("voice_score", "positioning_score", "findings", "verdict", "confidence"):
        if k not in out:
            raise ValueError(f"evaluator output missing '{k}'")
    if out["verdict"] not in VERDICTS:
        raise ValueError(f"unknown verdict: {out['verdict']!r}")
    for f in out["findings"]:
        if f.get("severity") not in ("must-fix", "consideration"):
            raise ValueError("each finding needs severity must-fix|consideration")
    c = out["confidence"]
    for k in ("why_chosen", "what_communicates", "standing", "risk"):
        c.setdefault(k, "")
    out.setdefault("comparison_note", "")
    out.setdefault("self_pushback", "")
    return out


# --- the spine --------------------------------------------------------------

def run_production(brief, *, config, writer_fn, evaluator_fn, voice_spec_text="",
                   pillars=None, source_excerpts=None, overrides=None,
                   today=None, run_id=None):
    today = today or date.today().isoformat()
    run_id = run_id or today
    fmt = brief.get("format", "short_form")
    channel = brief.get("channel", "neutral")
    pillars = pillars or []
    source_excerpts = source_excerpts or []
    rules = {"format": fmt, "channel": channel}

    # 1. Draft
    draft = validate_draft(writer_fn({
        "mode": "draft", "brief": brief, "voice_spec": voice_spec_text,
        "positioning_pillars": pillars, "sources": source_excerpts, "rules": rules,
    }))
    draft_text = draft["draft_text"]
    lint_draft_findings, stats1 = lint_draft(draft_text, fmt=fmt, channel=channel, overrides=overrides)

    # 2. Evaluate (once)
    ev = validate_evaluation(evaluator_fn({
        "brief": brief, "draft_text": draft_text, "voice_spec": voice_spec_text,
        "positioning_pillars": pillars, "format": fmt, "channel": channel,
    }))
    must_fixes = [f for f in ev["findings"] if f["severity"] == "must-fix"]
    needs_revision = bool(must_fixes) or ev["voice_score"] < 4 or ev["positioning_score"] < 4

    # 3. Bounded revision (exactly one cycle)
    declined, changes_applied, final_text = [], [], draft_text
    lint_final, preservation = lint_draft_findings, []
    if needs_revision:
        rev = validate_revision(writer_fn({
            "mode": "revise", "brief": brief, "draft_text": draft_text,
            "findings": ev["findings"], "voice_spec": voice_spec_text,
            "positioning_pillars": pillars, "rules": rules,
        }))
        final_text = rev["final_text"]
        declined = rev["declined"]
        changes_applied = rev["changes_applied"]
        draft["open_questions"] = draft["open_questions"] + rev["open_questions"]
        touchpoints = [f.get("quote", "") for f in must_fixes]
        preservation, _ = lint_draft(final_text, fmt=fmt, channel=channel,
                                     overrides=overrides, prev=draft_text,
                                     touchpoints=touchpoints)
        lint_final, _ = lint_draft(final_text, fmt=fmt, channel=channel, overrides=overrides)

    # 4. Write baseline + final + packet (private workspace)
    out_dir = Path(config["workspace_dir"]) / run_id / brief.get("idea_id", "idea")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "draft-v1.md").write_text(draft_text, encoding="utf-8")   # learning baseline
    (out_dir / "final.md").write_text(final_text, encoding="utf-8")
    packet_md = build_packet(brief, final_text, ev, declined, changes_applied,
                             stats1, lint_final + preservation, source_excerpts,
                             draft["open_questions"])
    (out_dir / "packet.md").write_text(packet_md, encoding="utf-8")

    return {
        "idea_id": brief.get("idea_id", ""),
        "format": fmt, "channel": channel,
        "verdict": ev["verdict"],
        "voice_score": ev["voice_score"], "positioning_score": ev["positioning_score"],
        "must_fixes": len(must_fixes), "revised": needs_revision,
        "changes_applied": changes_applied, "declined": declined,
        "lint_errors_final": sum(1 for f in lint_final + preservation if f["level"] == "error"),
        "packet_path": str(out_dir / "packet.md"),
        "baseline_path": str(out_dir / "draft-v1.md"),
        "final_path": str(out_dir / "final.md"),
    }


# --- packet assembly (user-facing "draft packet") ---------------------------

def build_packet(brief, final_text, ev, declined, changes_applied, stats,
                 lint_final, source_excerpts, open_questions) -> str:
    c = ev["confidence"]
    refs = brief.get("why_chosen", {}).get("evidence", []) or source_excerpts
    ref_lines = "\n".join(
        f"- {e.get('source', '')}:{e.get('ref', '')}" for e in refs) or "- (none recorded)"
    declined_lines = "\n".join(
        f"- {d.get('finding', '')} — declined: {d.get('reason', '')}" for d in declined) or "- None"
    applied = "\n".join(f"- {x}" for x in changes_applied) or "- None"
    q_lines = "\n".join(f"- {q}" for q in open_questions) if open_questions else "- None"
    lint_line = ("clean" if not any(f["level"] == "error" for f in lint_final)
                 else "; ".join(f["message"] for f in lint_final if f["level"] == "error"))

    return f"""# Draft — {brief.get('working_title', '')} — {brief.get('format', '')} · {brief.get('channel', '')}

## The draft
{final_text}

## Details
- Format / channel: {brief.get('format', '')} / {brief.get('channel', '')}
- Originating idea: {brief.get('idea_id', '')}
- Brief: {brief.get('premise', '')}
- Source references used:
{ref_lines}
- Lint (final): {lint_line}

## Scorecard
- Voice: {ev['voice_score']}/5
- Positioning Impact: {ev['positioning_score']}/5
- Must-fixes applied:
{applied}
- Evaluator suggestions declined by the writer:
{declined_lines}
- Questions for you:
{q_lines}

## Why CHAIN chose this
{c['why_chosen']}

## What this communicates
{c['what_communicates']}

## Why you have standing to say it
{c['standing']}

## Reasonable publication risk
{c['risk']}

## Editorial verdict
**{ev['verdict']}**
"""


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
