"""Bundle support: exactly two drafts (long_form + companion_post), one bundle packet."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.bundle import run_bundle, validate_bundle  # noqa: E402

IDEA = "IDEA-0009"
LONG = {"idea_id": IDEA, "working_title": "Legibility", "premise": "p",
        "format": "long_form", "channel": "medium", "primary_pillar": "current-and-fluent"}
COMP = {"idea_id": IDEA, "working_title": "Legibility (companion)", "premise": "p",
        "format": "companion_post", "channel": "linkedin", "relationship": "companion-of",
        "companion_angle": "origin-story", "primary_pillar": "current-and-fluent"}


def _eval_ok(voice=5, pos=5):
    return {"voice_score": voice, "positioning_score": pos, "findings": [],
            "verdict": "Strong candidate to publish",
            "confidence": {"why_chosen": "w", "what_communicates": "x",
                           "standing": "y", "risk": "z"}}


def _bundle_ok():
    return {"companion_creates_interest": "yes, teases the core tension",
            "companion_stands_alone": "yes, useful on its own",
            "unnecessarily_repetitive": "no; different openings",
            "channel_fit": "long fits medium, companion fits linkedin",
            "coherent_idea": "yes, one idea",
            "companion_angle": "origin-story", "findings": [],
            "verdict": "Strong candidate to publish"}


class TestBundle(unittest.TestCase):
    def _config(self):
        home = Path(tempfile.mkdtemp())
        return {"chain_home": str(home), "workspace_dir": str(home / "workspace")}

    def _writer(self, inp):
        if inp["mode"] == "draft":
            fmt = inp["brief"]["format"]
            if fmt == "long_form":
                return {"draft_text": " ".join(["A real long-form sentence about the idea."] * 40)}
            return {"draft_text": "A companion post that opens on the origin story, not a summary."}
        return {"final_text": "x", "addressed": [], "declined": []}

    def _evaluator(self, inp):
        return _bundle_ok() if inp.get("mode") == "bundle" else _eval_ok()

    def test_bundle_produces_two_drafts_and_one_packet(self):
        res = run_bundle(config=self._config(), long_brief=dict(LONG), companion_brief=dict(COMP),
                         writer_fn=self._writer, evaluator_fn=self._evaluator, today="2026-07-11")
        self.assertEqual(res["bundle_verdict"], "Strong candidate to publish")
        self.assertTrue(Path(res["bundle_packet_path"]).exists())
        self.assertTrue(Path(res["long"]["final_path"]).exists())
        self.assertTrue(Path(res["companion"]["final_path"]).exists())
        # the two pieces are written to distinct slugged subdirs under one idea
        self.assertNotEqual(res["long"]["final_path"], res["companion"]["final_path"])
        packet = Path(res["bundle_packet_path"]).read_text(encoding="utf-8")
        self.assertIn("Companion angle: origin-story", packet)

    def test_mismatched_idea_id_rejected(self):
        with self.assertRaises(ValueError):
            run_bundle(config=self._config(), long_brief=dict(LONG),
                       companion_brief={**COMP, "idea_id": "IDEA-9999"},
                       writer_fn=self._writer, evaluator_fn=self._evaluator)

    def test_non_bundle_formats_rejected(self):
        with self.assertRaises(ValueError):
            run_bundle(config=self._config(),
                       long_brief={**LONG, "format": "short_form"}, companion_brief=dict(COMP),
                       writer_fn=self._writer, evaluator_fn=self._evaluator)

    def test_bad_bundle_verdict_rejected(self):
        with self.assertRaises(ValueError):
            validate_bundle({**_bundle_ok(), "verdict": "Ship it"})


if __name__ == "__main__":
    unittest.main()
