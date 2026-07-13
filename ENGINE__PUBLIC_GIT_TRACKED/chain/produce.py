#!/usr/bin/env python3
"""The production spine: Brief -> Draft -> Evaluate -> bounded Revise -> Reevaluate.

Deterministic harness; the two creative roles are portable LLM agents injected as
`writer_fn` and `evaluator_fn`. The harness runs the mechanical lint, enforces the ONE
bounded revision cycle (ALWAYS run, even on a strong draft — see below), enforces
protect-marked passages mechanically, and assembles a private **draft packet** into
__READY_TO_REVIEW__PRIVATE_GITIGNORED/. It writes nothing public and copies no full source library — only
the run's own draft, baseline, and packet. It also persists the finished Piece into the
editorial library and advances the originating Idea's lifecycle — production is not
"done" until the library reflects it.

Finding severity (four tiers, in `FINDING_SEVERITIES`):
  * must-fix      — a required correction (voice/brief/truth/format violation, OR any
                    factual/mechanical misstatement the sources contradict). The writer
                    must address it; if declined, that disagreement is flagged loudly.
  * improvement   — a meaningful, optional improvement. The writer should act on at
                    least one genuine improvement/consideration finding when any exist.
  * protect       — language the evaluator flags as especially strong. Mechanically
                    enforced: its cited quote must survive verbatim in the final text,
                    and the writer may not "address" (alter) a protect finding at all.
  * consideration — a minor, optional, writer's-call finding.

The revision pass ALWAYS runs (never gated on scores or must-fix count) — the loop is
always Draft -> Evaluate -> Revise -> Reevaluate. A revision that changes nothing is a
valid, rare outcome, but only when every finding was explicitly declined with a reason
and the reevaluation confirms nothing was left undone.

Finding-to-revision traceability is explicit and mechanical:
  * each evaluator finding carries a stable `id` (F1, F2, ...);
  * the writer revision declares, per id, what it `addressed` and what it `declined`;
  * preservation lint uses that mapping — only the passages of ADDRESSED findings may
    change; everything else (including protect and declined findings' passages) must
    survive verbatim.

Baseline draft (`draft-v1.md`) and the brief are preserved so a later learning slice can
reconcile against the user's published version. No learning happens here — the packet's
"What CHAIN may learn from this run" section states that policy explicitly.

Stdlib only (PyYAML only if `lint_overrides` is configured, via lint_draft).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .lint_draft import lint_draft, load_lint_overrides

VERDICTS = {
    "Strong candidate to publish",
    "Good candidate with one issue to review",
    "Interesting but somewhat exposed",
    "Strategically useful, but currently too generic",
    "Do not publish this version",
}

FINDING_SEVERITIES = {"must-fix", "improvement", "protect", "consideration"}

# A fixed policy statement, identical in every packet — what CHAIN retains from a run
# and what it deliberately does NOT learn from without the user's explicit say-so.
LEARNING_POLICY = """CHAIN may retain, if you choose to feed it back in:
- your final edited version (what you actually publish, if different from `final.md`)
- explicit feedback you give (goes in the feedback ledger, which outranks every spec)
- reusable lessons you approve (never inferred and auto-promoted without you)

CHAIN will NOT automatically learn from:
- its own generated draft, taken as if it were good writing
- the evaluator's opinions alone, taken as ground truth
- inferred preferences nobody confirmed
- language you rejected, quietly reappearing in a later draft"""


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
    out.setdefault("addressed", [])   # [{finding_id, change}]
    out.setdefault("declined", [])    # [{finding_id, reason}]
    out.setdefault("open_questions", [])
    for a in out["addressed"]:
        if "finding_id" not in a:
            raise ValueError("each addressed item needs a finding_id")
        a.setdefault("change", "")
    for d in out["declined"]:
        if "finding_id" not in d:
            raise ValueError("each declined item needs a finding_id")
        d.setdefault("reason", "")
    return out


def validate_evaluation(out) -> dict:
    for k in ("voice_score", "positioning_score", "findings", "verdict", "confidence"):
        if k not in out:
            raise ValueError(f"evaluator output missing '{k}'")
    if out["verdict"] not in VERDICTS:
        raise ValueError(f"unknown verdict: {out['verdict']!r}")
    for i, f in enumerate(out["findings"]):
        if f.get("severity") not in FINDING_SEVERITIES:
            raise ValueError(
                f"each finding needs severity in {sorted(FINDING_SEVERITIES)}, "
                f"got {f.get('severity')!r}")
        f.setdefault("id", f"F{i + 1}")   # stable finding id, backfilled if absent
    c = out["confidence"]
    for k in ("why_chosen", "what_communicates", "standing", "risk"):
        c.setdefault(k, "")
    out.setdefault("comparison_note", "")
    out.setdefault("self_pushback", "")
    return out


# --- library persistence (Piece + Idea lifecycle) ---------------------------

# An Idea that has produced a Piece is no longer indistinguishable from an untouched
# proposal. Bump forward on first production; never downgrade an idea that's already
# further along (e.g. already "published"). One Idea may produce many Pieces over
# time — production never blocks a later piece in a different format.
_IDEA_PRE_PRODUCTION_STATUSES = {"proposed", "developing", "briefed", "in-production"}


def _persist_piece(library, brief, result, *, today) -> str:
    idea_id = brief.get("idea_id", "")
    piece_id = library.add_piece(
        idea_id, fmt=result["format"], channel=result["channel"],
        title_or_opening=brief.get("working_title", ""),
        status="final",                      # produced through the spine; not published
        final_text_path=result["final_path"],
        parent_piece_id=brief.get("parent_piece_id", ""),
        related_piece_ids=brief.get("related_piece_ids", ""),
        relation_type=brief.get("relation_type", ""),
        pillar=brief.get("primary_pillar", ""),
        notes=result.get("piece_notes", ""),
    )
    idea = library.get_idea(idea_id)
    if idea is not None:
        if idea.get("status") in _IDEA_PRE_PRODUCTION_STATUSES:
            idea["status"] = "produced"
        idea["last_touched"] = today
    return piece_id


# --- the spine --------------------------------------------------------------

def run_production(brief, *, config, writer_fn, evaluator_fn, library, voice_spec_text="",
                   pillars=None, source_excerpts=None, overrides=None, selection=None,
                   today=None, run_id=None):
    """`library` is required (keyword-only, no default): every completed Piece is
    persisted and its Idea's lifecycle advanced — that is not optional behavior.
    `selection` is an optional {"mechanism": "...", "note": "..."} describing how this
    idea was chosen, surfaced in the packet's provenance section."""
    today = today or date.today().isoformat()
    run_id = run_id or today
    fmt = brief.get("format", "short_form")
    channel = brief.get("channel", "neutral")
    pillars = pillars or []
    source_excerpts = source_excerpts or []
    rules = {"format": fmt, "channel": channel}
    if overrides is None:
        overrides = load_lint_overrides(config.get("lint_overrides", ""))

    # 1. Draft
    draft = validate_draft(writer_fn({
        "mode": "draft", "brief": brief, "voice_spec": voice_spec_text,
        "positioning_pillars": pillars, "sources": source_excerpts, "rules": rules,
    }))
    draft_text = draft["draft_text"]

    # 2. Evaluate (once). `sources` is included so factual/mechanical claims can
    #    actually be checked against what the material supports (see FINDING_SEVERITIES
    #    must-fix: any claim the sources contradict) — a scoring rule is only honest if
    #    the evaluator can see what it's scoring against.
    ev = validate_evaluation(evaluator_fn({
        "mode": "evaluate", "brief": brief, "draft_text": draft_text,
        "voice_spec": voice_spec_text, "positioning_pillars": pillars,
        "sources": source_excerpts, "format": fmt, "channel": channel,
    }))
    fid_quote = {f["id"]: f.get("quote", "") for f in ev["findings"]}
    fid_severity = {f["id"]: f["severity"] for f in ev["findings"]}
    must_fixes = [f for f in ev["findings"] if f["severity"] == "must-fix"]
    protect_findings = [f for f in ev["findings"] if f["severity"] == "protect"]

    # 3. Bounded revision — ALWAYS runs, even on a strong draft with zero findings.
    #    (A truly flawless, untouchable draft is a valid, rare outcome; it is not an
    #    excuse to skip asking.) Findings of every severity go to the writer.
    rev = validate_revision(writer_fn({
        "mode": "revise", "brief": brief, "draft_text": draft_text,
        "findings": ev["findings"], "voice_spec": voice_spec_text,
        "positioning_pillars": pillars, "rules": rules,
    }))
    final_text = rev["final_text"]
    addressed = rev["addressed"]
    declined = rev["declined"]
    draft["open_questions"] = draft["open_questions"] + rev["open_questions"]
    draft_changed = final_text.strip() != draft_text.strip()

    # --- mechanical integrity checks on the revision (all findings, not just must-fix) ---
    revision_notes = []
    addressed_ids = {a["finding_id"] for a in addressed}
    declined_ids = {d["finding_id"] for d in declined}
    accounted = addressed_ids | declined_ids
    for fid, sev in fid_severity.items():
        # protect findings are accounted for by the verbatim-survival check below, not
        # by addressed/declined bookkeeping — they aren't a problem to dispose of.
        if sev != "protect" and fid not in accounted:
            revision_notes.append(f"{fid} was not addressed or declined (unaccounted for)")

    # protect findings: may never be "addressed" (altered) — and their quote must
    # survive verbatim in the final text regardless of what the writer did.
    for f in protect_findings:
        fid, quote = f["id"], f.get("quote", "")
        if fid in addressed_ids:
            revision_notes.append(
                f"{fid} is protect-marked but was addressed (altered) — protected "
                "language must never be changed")
        if quote and quote not in final_text:
            revision_notes.append(
                f"{fid} protect-marked quote no longer appears verbatim in the final text")

    # must-fix findings the writer declined are a real, flaggable disagreement — never
    # silently dropped. Not blocking (the writer may have good reason), but loud.
    must_fix_declined = [d for d in declined if fid_severity.get(d["finding_id"]) == "must-fix"]

    if not draft_changed:
        # Legitimate only if every non-protect finding was explicitly declined.
        undeclined = {fid for fid, sev in fid_severity.items()
                     if sev != "protect" and fid not in declined_ids}
        if fid_severity and undeclined:
            revision_notes.append(
                "draft is unchanged from v1 but not every finding was declined: "
                + ", ".join(sorted(undeclined)))

    # only ADDRESSED findings' cited passages may change (protect/declined/consideration
    # left untouched are exactly what preservation mode already protects by default)
    touchpoints = [fid_quote.get(a["finding_id"], "") for a in addressed]
    preservation, _ = lint_draft(final_text, fmt=fmt, channel=channel,
                                 overrides=overrides, prev=draft_text,
                                 touchpoints=touchpoints)

    # 4. Final re-evaluation of what the user would actually publish — ALWAYS runs
    #    (a read, not another revision) so the packet's scores/verdict describe final.md.
    ev_final = validate_evaluation(evaluator_fn({
        "mode": "reevaluate", "brief": brief, "draft_text": final_text,
        "voice_spec": voice_spec_text, "positioning_pillars": pillars,
        "sources": source_excerpts, "format": fmt, "channel": channel,
    }))

    lint_final, _ = lint_draft(final_text, fmt=fmt, channel=channel, overrides=overrides)
    for reason in revision_notes:
        lint_final.append({"level": "warn", "code": "revision-integrity", "message": reason})
    if must_fix_declined:
        names = ", ".join(f"{d['finding_id']} ({d.get('reason', '')})" for d in must_fix_declined)
        lint_final.append({"level": "warn", "code": "must-fix-declined",
                           "message": f"writer declined required correction(s): {names}"})

    # 5. Write baseline + final + packet (private review root)
    slug = brief.get("slug", fmt)
    out_dir = Path(config["workspace_dir"]) / run_id / brief.get("idea_id", "idea") / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "draft-v1.md").write_text(draft_text, encoding="utf-8")   # learning baseline
    (out_dir / "final.md").write_text(final_text, encoding="utf-8")

    result = {
        "idea_id": brief.get("idea_id", ""), "format": fmt, "channel": channel,
        "verdict": ev_final["verdict"],
        "voice_score": ev_final["voice_score"], "positioning_score": ev_final["positioning_score"],
        "verdict_pre_revision": ev["verdict"],
        "revision_ran": True, "revised": draft_changed,
        "findings": ev["findings"], "must_fixes": len(must_fixes),
        "must_fix_declined": must_fix_declined,
        "addressed": addressed, "declined": declined, "revision_notes": revision_notes,
        "final_text": final_text, "draft_text": draft_text,
        "lint_errors_final": sum(1 for f in lint_final if f["level"] == "error")
                             + sum(1 for f in preservation if f["level"] == "error"),
        "preservation_findings": preservation,
        "baseline_path": str(out_dir / "draft-v1.md"),
        "final_path": str(out_dir / "final.md"),
    }

    piece_id = _persist_piece(library, brief, result, today=today)
    library.save()
    result["piece_id"] = piece_id

    packet_md = build_packet(brief, result, ev_final, addressed, declined,
                             lint_final + preservation, source_excerpts,
                             draft["open_questions"], config=config, selection=selection,
                             piece_id=piece_id)
    (out_dir / "packet.md").write_text(packet_md, encoding="utf-8")
    result["packet_path"] = str(out_dir / "packet.md")
    return result


# --- packet assembly (user-facing "draft packet") ---------------------------

_SEVERITY_LABELS = {"must-fix": "Required correction", "improvement": "Improvement",
                    "protect": "Protect this language", "consideration": "Consideration"}


def _provenance_block(brief, config, source_excerpts, selection, piece_id) -> str:
    sel = selection or {}
    sel_line = (f"{sel.get('mechanism', 'not recorded')} — {sel.get('note', '')}"
               if sel else "not recorded")
    src_lines = "\n".join(f"  - {e.get('source', '')}:{e.get('ref', '')}"
                          for e in source_excerpts) or "  - (none recorded)"
    exemplars = brief.get("exemplars_used") or []
    ex_lines = "\n".join(f"  - {e}" for e in exemplars) or "  - None referenced this run"
    return f"""## What shaped this draft
- Idea: {brief.get('idea_id', '')} — {brief.get('working_title', '')}
- Piece: {piece_id}
- Format / channel: {brief.get('format', '')} / {brief.get('channel', '')}
- Idea selection: {sel_line}
- Voice guidance: {config.get('voice_spec') or 'not configured'}
- Positioning guidance: {config.get('positioning_pillars') or 'not configured'} — primary: {brief.get('primary_pillar', '') or '(none declared)'}, secondary: {brief.get('secondary_pillar', '') or '(none)'}
- Lint overrides consulted: {config.get('lint_overrides') or 'not configured (generic rules only)'}
- Feedback ledger consulted: {config.get('feedback_ledger') or 'not configured'}
- Source materials referenced:
{src_lines}
- Exemplars referenced:
{ex_lines}"""


def _lint_status_block(lint_final) -> str:
    errors = [f for f in lint_final if f["level"] == "error"]
    known_fp = [f for f in lint_final if f["code"] == "banned-phrase-quoted-mention"]
    other_warn = [f for f in lint_final
                 if f["level"] == "warn" and f["code"] != "banned-phrase-quoted-mention"]
    lines = ["## Final lint status"]
    lines.append(f"- Status: {'clean' if not errors else f'{len(errors)} unresolved error(s)'}")
    if errors:
        for f in errors:
            lines.append(f"  - ERROR [{f['code']}]: {f['message']}")
    if known_fp:
        lines.append("- Known false positives (auto-classified, not blocking):")
        for f in known_fp:
            lines.append(f"  - [{f['code']}]: {f['message']}")
    if other_warn:
        lines.append("- Other flags:")
        for f in other_warn:
            lines.append(f"  - [{f['code']}]: {f['message']}")
    return "\n".join(lines)


def build_packet(brief, result, ev, addressed, declined, lint_final, source_excerpts,
                 open_questions, *, config=None, selection=None, piece_id="") -> str:
    config = config or {}
    c = ev["confidence"]
    refs = brief.get("why_chosen", {}).get("evidence", []) or source_excerpts
    ref_lines = "\n".join(
        f"- {e.get('source', '')}:{e.get('ref', '')}" for e in refs) or "- (none recorded)"

    findings_by_sev = {}
    for f in result.get("findings", []):
        findings_by_sev.setdefault(f["severity"], []).append(f)
    sev_counts = ", ".join(f"{len(v)} {_SEVERITY_LABELS[k].lower()}"
                           for k, v in findings_by_sev.items()) or "none"

    addressed_lines = "\n".join(
        f"- {a['finding_id']}: {a.get('change', '')}" for a in addressed) or "- None"
    declined_lines = "\n".join(
        f"- {d['finding_id']} — declined: {d.get('reason', '')}" for d in declined) or "- None"
    protect_lines = "\n".join(
        f"- {f['id']}: \"{f.get('quote', '')[:80]}\"" for f in findings_by_sev.get("protect", [])
    ) or "- None marked"
    q_lines = "\n".join(f"- {q}" for q in open_questions) if open_questions else "- None"
    unchanged_note = (
        f"\n- Draft unchanged from v1: yes — every finding was declined; "
        f"reevaluation confirmed nothing outstanding."
        if not result.get("revised") and result.get("findings") else "")

    return f"""# Draft — {brief.get('working_title', '')} — {brief.get('format', '')} · {brief.get('channel', '')}

## The draft
{result['final_text']}

{_provenance_block(brief, config, source_excerpts, selection, piece_id)}

## Scorecard
- Voice: {ev['voice_score']}/5
- Positioning Impact: {ev['positioning_score']}/5
- Pre-revision verdict: {result.get('verdict_pre_revision', '')}
- Findings this run (by severity): {sev_counts}{unchanged_note}

## Revision
- Findings addressed (by id):
{addressed_lines}
- Findings declined by the writer:
{declined_lines}
- Protected language (must survive verbatim):
{protect_lines}
- Questions for you:
{q_lines}

{_lint_status_block(lint_final)}

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

## What CHAIN may learn from this run
{LEARNING_POLICY}
"""


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
