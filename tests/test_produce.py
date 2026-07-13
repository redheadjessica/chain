"""Production spine: draft -> evaluate -> ALWAYS bounded revise -> reevaluate -> packet,
with explicit finding-id traceability, mapping-based preservation, protect-passage
enforcement, and Piece/Idea library persistence. Agents stubbed."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.editorial_library import EditorialLibrary  # noqa: E402
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


class ProduceTestBase(unittest.TestCase):
    def _config(self):
        home = Path(tempfile.mkdtemp())
        return {"chain_home": str(home), "workspace_dir": str(home / "workspace")}

    def _library(self, config, *, seed_idea=True):
        lib = EditorialLibrary.open(Path(config["chain_home"]) / "library")
        if seed_idea:
            # add_idea() mints its own sequential id; BRIEF hardcodes IDEA-0001, so
            # seed the row directly instead.
            lib.ideas.append({
                "idea_id": "IDEA-0001", "working_title": "Test piece", "premise": "A premise.",
                "status": "proposed", "source_type": "", "source_ref": "",
                "date_added": "2026-07-11", "last_touched": "2026-07-11",
                "intended_format": "", "intended_channel": "", "primary_pillar": "",
                "secondary_pillar": "", "user_interest": "", "user_feedback": "",
                "chain_opportunity": "", "timeliness": "", "expires": "",
                "related_work": "", "related_idea_ids": "", "rejected_reason": "",
            })
            lib.save()
        return lib


class TestProduce(ProduceTestBase):
    def test_strong_draft_still_gets_one_revision_pass(self):
        """The loop is ALWAYS draft -> evaluate -> revise -> reevaluate, even on a
        5/5 draft with zero findings. Revise mode must always be invoked."""
        modes = []

        def writer(inp):
            modes.append(inp["mode"])
            if inp["mode"] == "draft":
                return {"draft_text": "A clean short draft that says its one point plainly."}
            self.assertEqual(inp["findings"], [])
            return {"final_text": "A clean short draft that says its one point plainly.",
                    "addressed": [], "declined": []}

        cfg = self._config()
        res = run_production(BRIEF, config=cfg, writer_fn=writer, library=self._library(cfg),
                             evaluator_fn=lambda i: _eval(5, 5, [], "Strong candidate to publish"),
                             today="2026-07-11")
        self.assertEqual(modes, ["draft", "revise"])
        self.assertTrue(res["revision_ran"])
        self.assertFalse(res["revised"])   # text unchanged
        self.assertTrue(Path(res["baseline_path"]).exists())

    def test_must_fix_triggers_revision_with_finding_ids(self):
        modes = []

        def writer(inp):
            modes.append(inp["mode"])
            if inp["mode"] == "draft":
                return {"draft_text": "Strong opening line stays. The vague middle bit is weak here."}
            assert inp["findings"][0]["id"] == "F1"
            return {"final_text": "Strong opening line stays. The middle now names a concrete example.",
                    "addressed": [{"finding_id": "F1", "change": "made the vague middle concrete"}],
                    "declined": []}

        ev = _eval(3, 4, [{"id": "F1", "severity": "must-fix",
                           "quote": "The vague middle bit is weak", "why": "no specifics"}],
                   "Good candidate with one issue to review")
        cfg = self._config()
        res = run_production(BRIEF, config=cfg, writer_fn=writer, library=self._library(cfg),
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
        cfg = self._config()
        res = run_production(BRIEF, config=cfg, writer_fn=writer, library=self._library(cfg),
                             evaluator_fn=lambda i: ev, today="2026-07-11")
        self.assertEqual(res["declined"][0]["finding_id"], "F2")
        self.assertIn("F2 — declined:", Path(res["packet_path"]).read_text(encoding="utf-8"))

    def test_declined_must_fix_is_flagged_not_silently_dropped(self):
        def writer(inp):
            if inp["mode"] == "draft":
                return {"draft_text": "A draft with one deliberately debatable claim inside it here."}
            return {"final_text": "A draft with one deliberately debatable claim inside it here.",
                    "addressed": [],
                    "declined": [{"finding_id": "F1", "reason": "disagree — this is accurate as written"}]}

        ev = _eval(4, 4, [{"id": "F1", "severity": "must-fix",
                           "quote": "deliberately debatable claim", "why": "sources don't support this"}],
                   "Good candidate with one issue to review")
        cfg = self._config()
        res = run_production(BRIEF, config=cfg, writer_fn=writer, library=self._library(cfg),
                             evaluator_fn=lambda i: ev, today="2026-07-11")
        self.assertEqual(len(res["must_fix_declined"]), 1)
        packet = Path(res["packet_path"]).read_text(encoding="utf-8")
        self.assertIn("must-fix-declined", packet)

    def test_protect_finding_quote_must_survive(self):
        def writer(inp):
            if inp["mode"] == "draft":
                return {"draft_text": "This exact sentence is the best line in the whole piece today."}
            # violates protect: rewrites the protected sentence anyway
            return {"final_text": "This sentence got rewritten even though it was protected today.",
                    "addressed": [], "declined": []}

        ev = _eval(5, 5, [{"id": "F1", "severity": "protect",
                           "quote": "This exact sentence is the best line", "why": "keep this exactly"}],
                   "Strong candidate to publish")
        cfg = self._config()
        res = run_production(BRIEF, config=cfg, writer_fn=writer, library=self._library(cfg),
                             evaluator_fn=lambda i: ev, today="2026-07-11")
        self.assertTrue(any("protect-marked quote" in n for n in res["revision_notes"]))

    def test_protect_finding_cannot_be_addressed(self):
        def writer(inp):
            if inp["mode"] == "draft":
                return {"draft_text": "This exact sentence is the best line in the whole piece today."}
            return {"final_text": "This exact sentence is the best line in the whole piece today.",
                    "addressed": [{"finding_id": "F1", "change": "polished it slightly"}],
                    "declined": []}

        ev = _eval(5, 5, [{"id": "F1", "severity": "protect",
                           "quote": "This exact sentence is the best line", "why": "keep this exactly"}],
                   "Strong candidate to publish")
        cfg = self._config()
        res = run_production(BRIEF, config=cfg, writer_fn=writer, library=self._library(cfg),
                             evaluator_fn=lambda i: ev, today="2026-07-11")
        self.assertTrue(any("was addressed" in n for n in res["revision_notes"]))

    def test_protect_finding_needs_no_addressed_or_declined_disposition(self):
        """A protect finding is accounted for by the verbatim-survival check alone —
        it must not also be required in addressed/declined bookkeeping."""
        def writer(inp):
            if inp["mode"] == "draft":
                return {"draft_text": "This exact sentence is the best line in the whole piece today."}
            return {"final_text": "This exact sentence is the best line in the whole piece today.",
                    "addressed": [], "declined": []}   # F1 (protect) left out of both, correctly

        ev = _eval(5, 5, [{"id": "F1", "severity": "protect",
                           "quote": "This exact sentence is the best line", "why": "keep this exactly"}],
                   "Strong candidate to publish")
        cfg = self._config()
        res = run_production(BRIEF, config=cfg, writer_fn=writer, library=self._library(cfg),
                             evaluator_fn=lambda i: ev, today="2026-07-11")
        self.assertEqual(res["revision_notes"], [])

    def test_unaccounted_finding_is_flagged(self):
        def writer(inp):
            if inp["mode"] == "draft":
                return {"draft_text": "A draft with two separate things worth looking at here today."}
            return {"final_text": "A draft with two separate things worth looking at here today.",
                    "addressed": [], "declined": []}   # F1 never mentioned

        ev = _eval(4, 4, [{"id": "F1", "severity": "improvement",
                           "quote": "two separate things", "why": "could be sharper"}],
                   "Good candidate with one issue to review")
        cfg = self._config()
        res = run_production(BRIEF, config=cfg, writer_fn=writer, library=self._library(cfg),
                             evaluator_fn=lambda i: ev, today="2026-07-11")
        self.assertTrue(any("not addressed or declined" in n for n in res["revision_notes"]))

    def test_preservation_flags_uncited_rewrite(self):
        """If the writer changes a passage NO addressed finding cited, preservation errors."""
        def writer(inp):
            if inp["mode"] == "draft":
                return {"draft_text": ("The first sentence is fully fine and must stay exactly as it is. "
                                       "The second sentence has a clumsy phrasing that needs a real fix.")}
            return {"final_text": ("A completely rewritten and different first sentence appears now instead. "
                                   "The second sentence now reads cleanly and plainly for the reader."),
                    "addressed": [{"finding_id": "F1", "change": "fixed clumsy second sentence"}],
                    "declined": []}

        ev = _eval(3, 4, [{"id": "F1", "severity": "must-fix",
                           "quote": "clumsy phrasing that needs a real fix", "why": "awkward"}],
                   "Good candidate with one issue to review")
        cfg = self._config()
        res = run_production({**BRIEF, "format": "long_form", "channel": "neutral"},
                             config=cfg, writer_fn=writer, library=self._library(cfg),
                             evaluator_fn=lambda i: ev, today="2026-07-11")
        codes = {f["code"] for f in res["preservation_findings"] if f["level"] == "error"}
        self.assertIn("smoothing", codes)

    def test_do_not_publish_verdict_is_honest(self):
        def writer(inp):
            return ({"draft_text": "A generic draft anyone could have written today."}
                    if inp["mode"] == "draft"
                    else {"final_text": "A slightly less generic draft after one pass here.",
                          "addressed": [{"finding_id": "F1", "change": "tried"}], "declined": []})

        cfg = self._config()
        res = run_production(BRIEF, config=cfg, writer_fn=writer, library=self._library(cfg),
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
        with self.assertRaises(ValueError):
            validate_evaluation(_eval(4, 4, [{"severity": "urgent", "quote": "q", "why": "w"}],
                                      "Strong candidate to publish"))              # bad severity
        ev = validate_evaluation(_eval(4, 4, [{"severity": "must-fix", "quote": "q", "why": "w"}],
                                       "Strong candidate to publish"))
        self.assertEqual(ev["findings"][0]["id"], "F1")                          # id backfilled

    def test_all_four_severities_accepted(self):
        ev = _eval(5, 5, [
            {"id": "F1", "severity": "must-fix", "quote": "a", "why": "w"},
            {"id": "F2", "severity": "improvement", "quote": "b", "why": "w"},
            {"id": "F3", "severity": "protect", "quote": "c", "why": "w"},
            {"id": "F4", "severity": "consideration", "quote": "d", "why": "w"},
        ], "Strong candidate to publish")
        out = validate_evaluation(ev)
        self.assertEqual(len(out["findings"]), 4)


class TestPacketProvenance(ProduceTestBase):
    def _writer(self, inp):
        if inp["mode"] == "draft":
            return {"draft_text": "A clean short draft that says its one point plainly."}
        return {"final_text": "A clean short draft that says its one point plainly.",
                "addressed": [], "declined": []}

    def test_packet_includes_provenance_and_learning_policy(self):
        cfg = self._config()
        cfg["voice_spec"] = "/some/voice-spec.md"
        cfg["positioning_pillars"] = "/some/pillars.md"
        selection = {"mechanism": "selected by the user", "note": "a true quality ranking."}
        res = run_production(BRIEF, config=cfg, writer_fn=self._writer, library=self._library(cfg),
                             evaluator_fn=lambda i: _eval(5, 5, [], "Strong candidate to publish"),
                             selection=selection, today="2026-07-11")
        packet = Path(res["packet_path"]).read_text(encoding="utf-8")
        self.assertIn("What shaped this draft", packet)
        self.assertIn("/some/voice-spec.md", packet)
        self.assertIn("selected by the user", packet)
        self.assertIn("What CHAIN may learn from this run", packet)
        self.assertIn("will NOT automatically learn", packet)

    def test_missing_selection_is_reported_honestly(self):
        cfg = self._config()
        res = run_production(BRIEF, config=cfg, writer_fn=self._writer, library=self._library(cfg),
                             evaluator_fn=lambda i: _eval(5, 5, [], "Strong candidate to publish"),
                             today="2026-07-11")
        packet = Path(res["packet_path"]).read_text(encoding="utf-8")
        self.assertIn("not recorded", packet)


class TestLibraryPersistence(ProduceTestBase):
    def _writer(self, inp):
        if inp["mode"] == "draft":
            return {"draft_text": "A clean short draft that says its one point plainly."}
        return {"final_text": "A clean short draft that says its one point plainly.",
                "addressed": [], "declined": []}

    def test_piece_is_persisted_as_final_not_published(self):
        cfg = self._config()
        lib = self._library(cfg)
        res = run_production(BRIEF, config=cfg, writer_fn=self._writer, library=lib,
                             evaluator_fn=lambda i: _eval(5, 5, [], "Strong candidate to publish"),
                             today="2026-07-11")
        reloaded = EditorialLibrary.open(Path(cfg["chain_home"]) / "library")
        pieces = reloaded.pieces_for_idea("IDEA-0001")
        self.assertEqual(len(pieces), 1)
        piece = pieces[0]
        self.assertEqual(piece["piece_id"], res["piece_id"])
        self.assertEqual(piece["status"], "final")
        self.assertEqual(piece["pub_date"], "")
        self.assertEqual(piece["url"], "")
        self.assertEqual(piece["format"], "short_form")
        self.assertEqual(piece["channel"], "linkedin")

    def test_idea_status_advances_to_produced(self):
        cfg = self._config()
        lib = self._library(cfg)
        self.assertEqual(lib.get_idea("IDEA-0001")["status"], "proposed")
        run_production(BRIEF, config=cfg, writer_fn=self._writer, library=lib,
                       evaluator_fn=lambda i: _eval(5, 5, [], "Strong candidate to publish"),
                       today="2026-07-11")
        reloaded = EditorialLibrary.open(Path(cfg["chain_home"]) / "library")
        self.assertEqual(reloaded.get_idea("IDEA-0001")["status"], "produced")

    def test_idea_status_never_downgraded(self):
        cfg = self._config()
        lib = self._library(cfg)
        lib.get_idea("IDEA-0001")["status"] = "published"
        lib.save()
        lib = EditorialLibrary.open(Path(cfg["chain_home"]) / "library")
        run_production(BRIEF, config=cfg, writer_fn=self._writer, library=lib,
                       evaluator_fn=lambda i: _eval(5, 5, [], "Strong candidate to publish"),
                       today="2026-07-11")
        reloaded = EditorialLibrary.open(Path(cfg["chain_home"]) / "library")
        self.assertEqual(reloaded.get_idea("IDEA-0001")["status"], "published")

    def test_second_piece_same_idea_different_format(self):
        """Producing a short-form Piece must not block a later long-form Piece from
        the same Idea."""
        cfg = self._config()
        lib = self._library(cfg)
        run_production(BRIEF, config=cfg, writer_fn=self._writer, library=lib,
                       evaluator_fn=lambda i: _eval(5, 5, [], "Strong candidate to publish"),
                       today="2026-07-11")
        long_writer_calls = []

        def long_writer(inp):
            long_writer_calls.append(inp["mode"])
            text = " ".join(["A substantially developed long-form sentence."] * 60)
            if inp["mode"] == "draft":
                return {"draft_text": text}
            return {"final_text": text, "addressed": [], "declined": []}

        lib2 = EditorialLibrary.open(Path(cfg["chain_home"]) / "library")
        res2 = run_production({**BRIEF, "format": "long_form", "channel": "neutral", "slug": "long_form"},
                              config=cfg, writer_fn=long_writer, library=lib2,
                              evaluator_fn=lambda i: _eval(5, 5, [], "Strong candidate to publish"),
                              today="2026-07-12")
        reloaded = EditorialLibrary.open(Path(cfg["chain_home"]) / "library")
        pieces = reloaded.pieces_for_idea("IDEA-0001")
        self.assertEqual(len(pieces), 2)
        formats = {p["format"] for p in pieces}
        self.assertEqual(formats, {"short_form", "long_form"})


if __name__ == "__main__":
    unittest.main()
