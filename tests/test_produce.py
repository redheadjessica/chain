"""Production spine: draft -> evaluate -> bounded revise -> packet, with explicit
finding-id traceability and mapping-based preservation. Agents stubbed."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.produce import run_production, validate_evaluation, validate_revision  # noqa: E402

BRIEF = {
    "idea_id": "IDEA-0001", "working_title": "Test piece",
    "premise": "A premise.", "format": "short_form", "channel": "linkedin",
    "primary_pillar": "educates-clients",
    "why_chosen": {"evidence": [{"source": "faqs", "ref": "q.md"}]},
}


def _eval(voice, positioning, findings, verdict):
    return {"voice_score": voice, "positioning_score": positioning, "findings": findings,
            "verdict": verdict,
            "confidence": {"why_chosen": "w", "what_communicates": "x",
                           "standing": "y", "risk": "z"}}


class TestProduce(unittest.TestCase):
    def _config(self):
        home = Path(tempfile.mkdtemp())
        return {"chain_home": str(home), "workspace_dir": str(home / "workspace")}

    def test_strong_draft_skips_revision(self):
        modes = []

        def writer(inp):
            modes.append(inp["mode"])
            return {"draft_text": "A clean short draft that says its one point plainly."}

        res = run_production(BRIEF, config=self._config(), writer_fn=writer,
                             evaluator_fn=lambda i: _eval(5, 5, [], "Strong candidate to publish"),
                             today="2026-07-11")
        self.assertFalse(res["revised"])
        self.assertEqual(modes, ["draft"])
        self.assertTrue(Path(res["baseline_path"]).exists())

    def test_must_fix_triggers_one_revision_with_finding_ids(self):
        modes = []

        def writer(inp):
            modes.append(inp["mode"])
            if inp["mode"] == "draft":
                return {"draft_text": "Strong opening line stays. The vague middle bit is weak here."}
            # confirm the writer received findings WITH ids
            assert inp["findings"][0]["id"] == "F1"
            return {"final_text": "Strong opening line stays. The middle now names a concrete example.",
                    "addressed": [{"finding_id": "F1", "change": "made the vague middle concrete"}],
                    "declined": []}

        ev = _eval(3, 4, [{"id": "F1", "severity": "must-fix",
                           "quote": "The vague middle bit is weak", "why": "no specifics"}],
                   "Good candidate with one issue to review")
        res = run_production(BRIEF, config=self._config(), writer_fn=writer,
                             evaluator_fn=lambda i: ev, today="2026-07-11")
        self.assertTrue(res["revised"])
        self.assertEqual(modes, ["draft", "revise"])
        self.assertEqual(res["addressed"][0]["finding_id"], "F1")
        packet = Path(res["packet_path"]).read_text(encoding="utf-8")
        self.assertIn("F1: made the vague middle concrete", packet)

    def test_declined_finding_is_recorded(self):
        def writer(inp):
            if inp["mode"] == "draft":
                return {"draft_text": "A line with real energy here! The second line is genuinely weak."}
            return {"final_text": "A line with real energy here! The second line now says something concrete.",
                    "addressed": [{"finding_id": "F1", "change": "concretized second line"}],
                    "declined": [{"finding_id": "F2", "reason": "the exclamation is real energy, keeping it"}]}

        ev = _eval(3, 3, [
            {"id": "F1", "severity": "must-fix", "quote": "The second line is genuinely weak", "why": "vague"},
            {"id": "F2", "severity": "consideration", "quote": "real energy here!", "why": "drop the exclamation"},
        ], "Good candidate with one issue to review")
        res = run_production(BRIEF, config=self._config(), writer_fn=writer,
                             evaluator_fn=lambda i: ev, today="2026-07-11")
        self.assertEqual(res["declined"][0]["finding_id"], "F2")
        self.assertIn("F2 — declined:", Path(res["packet_path"]).read_text(encoding="utf-8"))

    def test_preservation_flags_uncited_rewrite(self):
        """If the writer changes a passage NO addressed finding cited, preservation errors."""
        def writer(inp):
            if inp["mode"] == "draft":
                return {"draft_text": ("The first sentence is fully fine and must stay exactly as it is. "
                                       "The second sentence has a clumsy phrasing that needs a real fix.")}
            # addressed F1 (second sentence) but ALSO rewrote the uncited first sentence
            return {"final_text": ("A completely rewritten and different first sentence appears now instead. "
                                   "The second sentence now reads cleanly and plainly for the reader."),
                    "addressed": [{"finding_id": "F1", "change": "fixed clumsy second sentence"}],
                    "declined": []}

        ev = _eval(3, 4, [{"id": "F1", "severity": "must-fix",
                           "quote": "clumsy phrasing that needs a real fix", "why": "awkward"}],
                   "Good candidate with one issue to review")
        res = run_production({**BRIEF, "format": "long_form", "channel": "neutral"},
                             config=self._config(), writer_fn=writer,
                             evaluator_fn=lambda i: ev, today="2026-07-11")
        codes = {f["code"] for f in res["preservation_findings"] if f["level"] == "error"}
        self.assertIn("smoothing", codes)

    def test_do_not_publish_verdict_is_honest(self):
        def writer(inp):
            return ({"draft_text": "A generic draft anyone could have written today."}
                    if inp["mode"] == "draft"
                    else {"final_text": "A slightly less generic draft after one pass here.",
                          "addressed": [{"finding_id": "F1", "change": "tried"}], "declined": []})

        res = run_production(BRIEF, config=self._config(), writer_fn=writer,
                             evaluator_fn=lambda i: _eval(
                                 2, 2, [{"id": "F1", "severity": "must-fix",
                                         "quote": "generic draft", "why": "no pillar"}],
                                 "Do not publish this version"),
                             today="2026-07-11")
        self.assertEqual(res["verdict"], "Do not publish this version")

    def test_validation_guards(self):
        with self.assertRaises(ValueError):
            validate_evaluation(_eval(4, 4, [], "Ship it"))                       # bad verdict
        with self.assertRaises(ValueError):
            validate_revision({"final_text": "x", "addressed": [{"change": "y"}]})  # no finding_id
        ev = validate_evaluation(_eval(4, 4, [{"severity": "must-fix", "quote": "q", "why": "w"}],
                                       "Strong candidate to publish"))
        self.assertEqual(ev["findings"][0]["id"], "F1")                          # id backfilled


if __name__ == "__main__":
    unittest.main()
