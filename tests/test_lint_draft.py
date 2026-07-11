"""Deterministic draft lint: mechanical rules and preservation mode."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.lint_draft import has_errors, lint_draft  # noqa: E402


def codes(findings, level=None):
    return {f["code"] for f in findings if level is None or f["level"] == level}


class TestLintMechanical(unittest.TestCase):
    def test_length_bounds_by_format(self):
        long_text = " ".join(["word"] * 500)
        f, _ = lint_draft(long_text, fmt="short_form", channel="neutral")
        self.assertIn("too-long", codes(f, "error"))
        f2, _ = lint_draft(long_text, fmt="long_form", channel="neutral")
        self.assertNotIn("too-long", codes(f2, "error"))

    def test_banned_generic_phrase(self):
        f, _ = lint_draft("We should leverage this insight to delve deeper. " * 3,
                          fmt="short_form", channel="neutral")
        self.assertIn("banned-phrase", codes(f, "error"))

    def test_personal_overrides(self):
        f, _ = lint_draft("Let's circle back on this later and align. " * 2,
                          fmt="short_form", channel="neutral",
                          overrides={"banned_phrases": ["circle back"]})
        self.assertIn("banned-phrase", codes(f, "error"))

    def test_linkedin_forbids_body_links(self):
        text = "Here is a great [resource](https://example.com/x) you should read now."
        f, _ = lint_draft(text, fmt="short_form", channel="linkedin")
        self.assertIn("body-links", codes(f, "error"))
        f2, _ = lint_draft(text, fmt="short_form", channel="neutral")
        self.assertNotIn("body-links", codes(f2, "error"))

    def test_repeated_punctuation(self):
        f, _ = lint_draft("This is amazing!! Really?? " * 4, fmt="short_form", channel="neutral")
        self.assertIn("repeated-punct", codes(f, "error"))

    def test_lint_never_judges_quality(self):
        """A clean, plain draft passes — lint does not judge whether it is interesting."""
        text = ("Shaving right before your appointment resets the growth clock. "
                "Come in with about two weeks of growth and we can actually work.")
        f, _ = lint_draft(text, fmt="short_form", channel="linkedin")
        self.assertFalse(has_errors(f))


class TestPreservation(unittest.TestCase):
    def test_removed_link_is_smoothing_error(self):
        prev = "A point worth making, see [the guide](https://example.com/g) for more depth here."
        new = "A point worth making, with more depth to consider here today."
        f, _ = lint_draft(new, fmt="long_form", channel="neutral",
                          prev=prev, touchpoints=[])
        self.assertIn("smoothing", codes(f, "error"))

    def test_uncited_sentence_rewrite_is_smoothing_error(self):
        prev = ("The first line stays exactly as it was originally written here. "
                "The second line has a clumsy phrasing that needs fixing badly.")
        # rewrote the FIRST (uncited) sentence, not the cited second one
        new = ("A totally different opening sentence with new wording entirely now. "
               "The second line has a clumsy phrasing that needs fixing badly.")
        f, _ = lint_draft(new, fmt="long_form", channel="neutral",
                          prev=prev, touchpoints=["clumsy phrasing that needs fixing"])
        self.assertIn("smoothing", codes(f, "error"))

    def test_cited_change_is_allowed(self):
        prev = ("The first line stays exactly as it was originally written here today. "
                "The second line has a clumsy phrasing that needs fixing badly now.")
        new = ("The first line stays exactly as it was originally written here today. "
               "The second line now reads cleanly and says the point plainly instead.")
        f, _ = lint_draft(new, fmt="long_form", channel="neutral",
                          prev=prev, touchpoints=["clumsy phrasing that needs fixing"])
        self.assertNotIn("smoothing", codes(f, "error"))


if __name__ == "__main__":
    unittest.main()
