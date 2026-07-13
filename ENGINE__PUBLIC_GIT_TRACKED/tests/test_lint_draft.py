"""Deterministic draft lint: mechanical rules and preservation mode."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.lint_draft import has_errors, lint_draft, load_lint_overrides  # noqa: E402


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

    def test_quoted_mention_of_banned_phrase_is_not_an_error(self):
        """Citing a banned phrase as an example ('no "leverage"') is a mention, not a
        live use — downgraded to a warn-level known false positive, not blocked."""
        text = ('A lint that bans phrases like "leverage" and "seamless" from ever '
                'appearing in a draft, mechanically, every single time it runs.')
        f, _ = lint_draft(text, fmt="short_form", channel="neutral")
        self.assertNotIn("banned-phrase", codes(f, "error"))
        self.assertIn("banned-phrase-quoted-mention", codes(f, "warn"))
        self.assertFalse(has_errors(f))

    def test_live_use_of_banned_phrase_still_errors(self):
        text = "We need to leverage this insight across every single team meeting today."
        f, _ = lint_draft(text, fmt="short_form", channel="neutral")
        self.assertIn("banned-phrase", codes(f, "error"))

    def test_mixed_quoted_and_live_use_classified_separately(self):
        text = ('The lint bans "leverage" as a word, but somehow this draft still '
                'manages to leverage the exact thing it was supposed to avoid entirely.')
        f, _ = lint_draft(text, fmt="short_form", channel="neutral")
        self.assertIn("banned-phrase", codes(f, "error"))
        self.assertIn("banned-phrase-quoted-mention", codes(f, "warn"))

    def test_channel_pack_override_merges(self):
        text = "One two three four five six seven eight nine ten eleven twelve words."
        overrides = {"channels": {"linkedin": {"max_external_links_in_body": 2}}}
        text_with_links = text + " [a](https://x.com/1) [b](https://x.com/2)"
        f, _ = lint_draft(text_with_links, fmt="short_form", channel="linkedin",
                          overrides=overrides)
        self.assertNotIn("body-links", codes(f, "error"))


class TestLoadLintOverrides(unittest.TestCase):
    def test_missing_path_returns_empty(self):
        self.assertEqual(load_lint_overrides(""), {})
        self.assertEqual(load_lint_overrides("/nonexistent/path.yaml"), {})

    def test_loads_watch_words_and_banned_phrases(self):
        tmp = Path(tempfile.mkdtemp()) / "overrides.yaml"
        tmp.write_text("banned_phrases:\n  - circle back\nwatch_words:\n  - quietly\n  - actually\n",
                       encoding="utf-8")
        ov = load_lint_overrides(str(tmp))
        self.assertEqual(ov["banned_phrases"], ["circle back"])
        self.assertEqual(ov["watch_words"], ["quietly", "actually"])

    def test_loaded_watch_words_flow_into_lint(self):
        tmp = Path(tempfile.mkdtemp()) / "overrides.yaml"
        tmp.write_text("watch_words:\n  - quietly\n", encoding="utf-8")
        ov = load_lint_overrides(str(tmp))
        f, _ = lint_draft("It was quietly getting worse every single day this happened.",
                          fmt="short_form", channel="neutral", overrides=ov)
        self.assertIn("watch-word", codes(f, "warn"))


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

    def test_cited_quote_spanning_two_sentences_is_allowed(self):
        """A finding's quote can span a sentence boundary ('X. Y.'). Each half must
        still be recognized as cited even though neither is the full touchpoint."""
        prev = ("So when I built a system, the hard part wasn't generation. "
                "It was teaching it to defer instead of bluff. "
                "The second unrelated sentence stays exactly as it was originally written.")
        new = ("So when I built a system, the hardest part was teaching it to defer instead of bluff. "
              "The second unrelated sentence stays exactly as it was originally written.")
        f, _ = lint_draft(new, fmt="long_form", channel="neutral", prev=prev,
                          touchpoints=["the hard part wasn't generation. it was teaching it to defer instead of bluff."])
        self.assertNotIn("smoothing", codes(f, "error"))

    def test_merging_two_cited_sentences_into_one_is_allowed(self):
        """A revision that correctly MERGES two cited sentences into one shouldn't
        false-positive just because no single new sentence is character-similar
        enough to either old fragment on its own."""
        prev = "The old opening line stays untouched here today. The vague middle bit needs work badly."
        new = "The old opening line stays untouched here today, though the middle now names a concrete example."
        f, _ = lint_draft(new, fmt="long_form", channel="neutral", prev=prev,
                          touchpoints=["The vague middle bit needs work badly"])
        self.assertNotIn("smoothing", codes(f, "error"))

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
