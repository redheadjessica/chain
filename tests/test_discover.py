"""Discover harness: input assembly, output validation, deterministic selection,
dedup into the backlog, and brief development. The LLM is stubbed."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.editorial_library import EditorialLibrary  # noqa: E402
from chain.discover import (  # noqa: E402
    build_discoverer_input, develop_briefs, parse_pillars, run_discoverer,
    seeds_to_backlog, select_seeds,
)

REPO = Path(__file__).resolve().parent.parent


def _seed(title, premise, lens, pillar="", **extra):
    d = {"working_title": title, "premise": premise, "lens": lens,
         "evidence": [{"source": "s", "ref": "a.md", "why": "x"}],
         "primary_pillar": pillar}
    d.update(extra)
    return d


class TestDiscover(unittest.TestCase):
    def _lib(self):
        d = Path(tempfile.mkdtemp())
        return EditorialLibrary(d / "ideas.csv", d / "pieces.csv")

    def test_parse_pillars_from_studio_persona(self):
        pillars = parse_pillars(REPO / "examples" / "demo-home-studio" / "positioning-pillars.md")
        ids = {p["id"] for p in pillars}
        self.assertIn("gentle-and-reassuring", ids)
        self.assertNotIn("id", ids)  # header row skipped

    def test_build_input_groups_docs_by_source(self):
        lib = self._lib()
        corpus = [
            {"source": "faqs", "ref": "q.md", "roles": ["questions"], "title": "Q", "excerpt": "..."},
            {"source": "faqs", "ref": "r.md", "roles": ["questions"], "title": "R", "excerpt": "..."},
            {"source": "reviews", "ref": "v.md", "roles": ["reviews"], "title": "V", "excerpt": "..."},
        ]
        inp = build_discoverer_input({"positioning_pillars": None}, corpus, lib, max_seeds=5)
        names = {s["name"] for s in inp["sources"]}
        self.assertEqual(names, {"faqs", "reviews"})
        self.assertEqual(len(inp["lenses"]), 8)

    def test_output_validation_rejects_bad_shape(self):
        with self.assertRaises(ValueError):
            run_discoverer({}, lambda i: {"seeds": [{"working_title": "x"}]})  # missing fields
        ok = run_discoverer({}, lambda i: {"seeds": []})
        self.assertEqual(ok["coverage_notes"], [])

    def test_select_drops_exact_backlog_dupes_and_caps(self):
        lib = self._lib()
        lib.add_idea("Existing idea", "A premise that already exists.", today="2026-01-01")
        seeds = [
            _seed("Existing idea", "A premise that already exists.", "fresh-lesson"),  # dup
            _seed("Idea A", "Distinct premise one.", "fresh-lesson", "p1"),
            _seed("Idea B", "Distinct premise two.", "repeated-question", "p2"),
            _seed("Idea C", "Distinct premise three.", "converging-signal", "p3"),
        ]
        picked, skipped = select_seeds(seeds, lib, max_n=2)
        self.assertEqual(len(picked), 2)
        reasons = " ".join(r for _, r in skipped)
        self.assertIn("already in backlog", reasons)

    def test_coverage_guard_seed_is_not_an_idea(self):
        lib = self._lib()
        picked, skipped = select_seeds(
            [_seed("skip me", "already covered topic", "coverage-guard")], lib, max_n=5)
        self.assertEqual(picked, [])

    def test_seeds_to_backlog_and_briefs(self):
        lib = self._lib()
        seeds = [_seed("New idea", "A genuinely new premise.", "translation-opportunity",
                       "educates-clients", suggested_format="short_form",
                       suggested_channel="instagram", rationale="clients keep asking")]
        pairs = seeds_to_backlog(seeds, lib, today="2026-03-01")
        self.assertEqual(len(pairs), 1)
        idea = lib.get_idea(pairs[0][0])
        self.assertEqual(idea["source_type"], "discover")
        self.assertEqual(idea["primary_pillar"], "educates-clients")
        briefs = develop_briefs(pairs, default_channel="neutral")
        self.assertEqual(briefs[0]["format"], "short_form")
        self.assertEqual(briefs[0]["why_chosen"]["lens"], "translation-opportunity")


if __name__ == "__main__":
    unittest.main()
