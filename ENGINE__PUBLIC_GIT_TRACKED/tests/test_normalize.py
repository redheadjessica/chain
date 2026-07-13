"""Corpus normalization: excerpts/titles, roles, and incremental reuse."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.normalize import build_corpus_index  # noqa: E402


class TestNormalize(unittest.TestCase):
    def _config(self):
        home = Path(tempfile.mkdtemp())
        src = home / "src"
        src.mkdir()
        (src / "a.md").write_text("# Hello Title\n\nSome body text here.\n", encoding="utf-8")
        return {
            "chain_home": str(home),
            "sources": [{"name": "s", "type": "text", "path": str(src),
                         "roles": ["published"], "include": ["*.md"]}],
        }, src

    def test_index_has_title_excerpt_roles(self):
        config, _ = self._config()
        idx = build_corpus_index(config)
        self.assertEqual(len(idx), 1)
        e = idx[0]
        self.assertEqual(e["title"], "Hello Title")
        self.assertIn("Some body text", e["excerpt"])
        self.assertEqual(e["roles"], ["published"])
        self.assertTrue(e["sha256"])

    def test_incremental_reuse_then_reexcerpt_on_change(self):
        config, src = self._config()
        first = build_corpus_index(config)
        sha1 = first[0]["sha256"]
        # unchanged: same hash reused
        second = build_corpus_index(config)
        self.assertEqual(second[0]["sha256"], sha1)
        # change the file: new hash + new excerpt
        (src / "a.md").write_text("# Different\n\nBrand new content.\n", encoding="utf-8")
        third = build_corpus_index(config)
        self.assertNotEqual(third[0]["sha256"], sha1)
        self.assertEqual(third[0]["title"], "Different")


if __name__ == "__main__":
    unittest.main()
