"""Source connectors: include/exclude walking and deterministic idea harvesting."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.sources import Source, harvest_ideas, walk_source  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEMO = REPO / "examples" / "demo-sources"


class TestWalking(unittest.TestCase):
    def test_include_and_exclude(self):
        root = Path(tempfile.mkdtemp())
        (root / "a.md").write_text("keep", encoding="utf-8")
        (root / "b.txt").write_text("drop by include", encoding="utf-8")
        (root / "_work").mkdir()
        (root / "_work" / "c.md").write_text("drop by exclude", encoding="utf-8")
        src = Source(name="s", type="longform", path=str(root),
                     include=["*.md"], exclude=["**/_work/**"])
        found = {rel for _, rel in walk_source(src)}
        self.assertEqual(found, {"a.md"})

    def test_missing_root_yields_nothing(self):
        src = Source(name="s", type="longform", path="/no/such/dir")
        self.assertEqual(list(walk_source(src)), [])


class TestHarvest(unittest.TestCase):
    def test_harvest_numbered_list_under_marker(self):
        text = (
            "# Application\n\n## Role analysis\nSome prose.\n\n"
            "## Writing ideas\n"
            "1. Why legible AI is a product surface — expand the note.\n"
            "2. The activation metric that predicts nothing.\n"
            "3. What three roles kept asking about.\n\n"
            "## Something else\n- not an idea\n"
        )
        ideas = harvest_ideas(text, "Writing ideas")
        self.assertEqual(len(ideas), 3)
        self.assertEqual(ideas[0][0], "Why legible AI is a product surface")
        self.assertTrue(ideas[1][1].startswith("The activation metric"))

    def test_no_marker_no_ideas(self):
        self.assertEqual(harvest_ideas("# Title\n- a\n- b\n", "Writing ideas"), [])

    def test_demo_application_file_harvests_three(self):
        text = (DEMO / "applications" / "northwind-senior-pm" /
                "application_output.md").read_text(encoding="utf-8")
        self.assertEqual(len(harvest_ideas(text, "Writing ideas")), 3)


if __name__ == "__main__":
    unittest.main()
