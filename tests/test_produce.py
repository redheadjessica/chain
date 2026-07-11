"""Production spine: draft -> evaluate -> bounded revise -> packet. Agents stubbed."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.produce import run_production, validate_evaluation  # noqa: E402

BRIEF = {
    "idea_id": "IDEA-0001", "working_title": "Test piece",
    "premise": "A premise.", "format": "short_form", "channel": "linkedin",
    "primary_pillar": "educates-clients",
    "why_chosen": {"evidence": [{"source": "faqs", "ref": "q.md"}]},
}


def _eval(voice, positioning, findings, verdict):
    return {
        "voice_score": voice, "positioning_score": positioning, "findings": findings,
        "verdict": verdict,
        "confidence": {"why_chosen": "w", "what_communicates": "x",
                       "standing": "y", "risk": "z"},
    }


class TestProduce(unittest.TestCase):
    def _config(self):
        home = Path(tempfile.mkdtemp())
        return {"chain_home": str(home), "workspace_dir": str(home / "workspace")}

    def test_strong_draft_skips_revision(self):
        writer_calls = []

        def writer(inp):
            writer_calls.append(inp["mode"])
            return {"draft_text": "A clean short draft that says its one point plainly."}

        def evaluator(inp):
            return _eval(5, 5, [], "Strong candidate to publish")

        res = run_production(BRIEF, config=self._config(), writer_fn=writer,
                             evaluator_fn=evaluator, today="2026-07-10")
        self.assertFalse(res["revised"])
        self.assertEqual(writer_calls, ["draft"])       # no revise call
        self.assertEqual(res["verdict"], "Strong candidate to publish")
        self.assertTrue(Path(res["packet_path"]).exists())
        self.assertTrue(Path(res["baseline_path"]).exists())   # baseline preserved

    def test_must_fix_triggers_one_revision(self):
        modes = []

        def writer(inp):
            modes.append(inp["mode"])
            if inp["mode"] == "draft":
                return {"draft_text": "First draft with a weak line to fix here."}
            return {"final_text": "First draft with a strong line to fix here.",
                    "changes_applied": ["tightened the weak line"],
                    "declined": [{"finding": "drop the exclamation", "reason": "energy is real"}]}

        def evaluator(inp):
            return _eval(3, 4, [{"severity": "must-fix", "quote": "weak line", "why": "vague"}],
                         "Good candidate with one issue to review")

        res = run_production(BRIEF, config=self._config(), writer_fn=writer,
                             evaluator_fn=evaluator, today="2026-07-10")
        self.assertTrue(res["revised"])
        self.assertEqual(modes, ["draft", "revise"])   # exactly one revision
        self.assertEqual(len(res["declined"]), 1)
        packet = Path(res["packet_path"]).read_text(encoding="utf-8")
        self.assertIn("declined: energy is real", packet)
        self.assertIn("Good candidate with one issue to review", packet)

    def test_do_not_publish_verdict_is_honest(self):
        def writer(inp):
            if inp["mode"] == "draft":
                return {"draft_text": "A generic draft anyone could have written today."}
            return {"final_text": "A slightly less generic draft after one pass here."}

        def evaluator(inp):
            return _eval(2, 2, [{"severity": "must-fix", "quote": "generic draft", "why": "no pillar"}],
                         "Do not publish this version")

        res = run_production(BRIEF, config=self._config(), writer_fn=writer,
                             evaluator_fn=evaluator, today="2026-07-10")
        self.assertEqual(res["verdict"], "Do not publish this version")

    def test_bad_verdict_rejected(self):
        with self.assertRaises(ValueError):
            validate_evaluation(_eval(4, 4, [], "Ship it"))


if __name__ == "__main__":
    unittest.main()
