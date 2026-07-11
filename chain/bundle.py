#!/usr/bin/env python3
"""Bundle support: a long-form Draft + a companion Draft, one Idea, one bundle packet.

Fixed to EXACTLY two drafts in V1 (long-form + companion). This is not campaign
orchestration. Each draft passes through the normal single-draft production spine
(`run_production`), then the same evaluator runs ONCE more in **bundle mode** over the
pair, and one private **bundle packet** is written.

The companion must not merely summarize the long-form draft; the bundle evaluator checks
that it takes an intentional angle, stands alone, avoids redundancy, fits each channel,
and that the two communicate a coherent idea.

Stdlib only.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .produce import VERDICTS, run_production

COMPANION_ANGLES = {
    "origin-story", "central-tension", "one-example", "related-observation",
    "why-it-was-written", "one-compelling-observation",
}


def validate_bundle(out) -> dict:
    for k in ("companion_creates_interest", "companion_stands_alone",
              "unnecessarily_repetitive", "channel_fit", "coherent_idea",
              "companion_angle", "verdict"):
        if k not in out:
            raise ValueError(f"bundle evaluation missing '{k}'")
    if out["verdict"] not in VERDICTS:
        raise ValueError(f"unknown bundle verdict: {out['verdict']!r}")
    out.setdefault("findings", [])
    return out


def run_bundle(*, config, long_brief, companion_brief, writer_fn, evaluator_fn,
               voice_spec_text="", pillars=None, long_sources=None,
               companion_sources=None, overrides=None, today=None, run_id=None):
    if long_brief.get("idea_id") != companion_brief.get("idea_id"):
        raise ValueError("a bundle's long-form and companion must share one idea_id")
    if long_brief.get("format") != "long_form" or companion_brief.get("format") != "companion_post":
        raise ValueError("a V1 bundle is exactly {long_form, companion_post}")
    today = today or date.today().isoformat()
    run_id = run_id or today
    long_brief.setdefault("slug", "long_form")
    companion_brief.setdefault("slug", "companion_post")

    long_res = run_production(long_brief, config=config, writer_fn=writer_fn,
                              evaluator_fn=evaluator_fn, voice_spec_text=voice_spec_text,
                              pillars=pillars, source_excerpts=long_sources,
                              overrides=overrides, today=today, run_id=run_id)
    comp_res = run_production(companion_brief, config=config, writer_fn=writer_fn,
                             evaluator_fn=evaluator_fn, voice_spec_text=voice_spec_text,
                             pillars=pillars, source_excerpts=companion_sources,
                             overrides=overrides, today=today, run_id=run_id)

    bundle = validate_bundle(evaluator_fn({
        "mode": "bundle",
        "long_brief": long_brief, "companion_brief": companion_brief,
        "long_draft": long_res["final_text"], "companion_draft": comp_res["final_text"],
        "positioning_pillars": pillars or [],
    }))

    out_dir = Path(config["workspace_dir"]) / run_id / long_brief["idea_id"]
    packet = build_bundle_packet(long_brief, companion_brief, long_res, comp_res, bundle)
    (out_dir / "bundle-packet.md").write_text(packet, encoding="utf-8")

    return {
        "idea_id": long_brief["idea_id"],
        "long": long_res, "companion": comp_res, "bundle": bundle,
        "bundle_verdict": bundle["verdict"],
        "bundle_packet_path": str(out_dir / "bundle-packet.md"),
    }


def build_bundle_packet(long_brief, companion_brief, long_res, comp_res, bundle) -> str:
    b = bundle
    bf = "\n".join(f"- [{f.get('severity', '')}] {f.get('why', '')}"
                   for f in b.get("findings", [])) or "- None"
    return f"""# Bundle — {long_brief.get('working_title', '')}

Idea: {long_brief.get('idea_id', '')} · two Drafts (long-form + companion)

## Long-form draft — {long_brief.get('channel', '')}
{long_res['final_text']}

- Voice {long_res['voice_score']}/5 · Positioning {long_res['positioning_score']}/5 · verdict: {long_res['verdict']}

## Companion draft — {companion_brief.get('channel', '')}
{comp_res['final_text']}

- Voice {comp_res['voice_score']}/5 · Positioning {comp_res['positioning_score']}/5 · verdict: {comp_res['verdict']}

## Bundle assessment
- Companion angle: {b['companion_angle']}
- Creates interest in the long-form piece: {b['companion_creates_interest']}
- Stands alone on its own value: {b['companion_stands_alone']}
- Unnecessarily repetitive: {b['unnecessarily_repetitive']}
- Fits each channel: {b['channel_fit']}
- Coherent single idea: {b['coherent_idea']}
- Pair findings:
{bf}

## Bundle verdict
**{b['verdict']}**
"""
