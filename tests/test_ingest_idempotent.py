"""Idempotent ingestion: unchanged sources add nothing; dedup prevents duplicates."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.editorial_library import EditorialLibrary  # noqa: E402
from chain.ingest import IngestLedger, run_ingest  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEMO_APPS = REPO / "examples" / "demo-sources" / "applications"


class TestIngestIdempotent(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        # copy the demo applications into a scratch source we can mutate
        self.src = self.home / "sources" / "applications"
        shutil.copytree(DEMO_APPS, self.src)
        self.config = {
            "chain_home": str(self.home),
            "library_dir": str(self.home / "library"),
            "sources": [{
                "name": "applications", "type": "job_applications",
                "path": str(self.src), "include": ["*.md"],
                "idea_marker": "Writing ideas", "enabled": True,
            }],
        }

    def _lib(self):
        return EditorialLibrary.open(self.config["library_dir"])

    def test_first_run_harvests_then_second_run_is_noop(self):
        first = run_ingest(self.config, today="2026-02-01")
        self.assertEqual(first.ideas_added, 3)
        self.assertEqual(len(self._lib().ideas), 3)

        second = run_ingest(self.config, today="2026-02-02")
        self.assertEqual(second.ideas_added, 0)          # unchanged -> nothing added
        self.assertEqual(second.unchanged, second.files_seen)
        self.assertEqual(len(self._lib().ideas), 3)      # backlog unchanged

    def test_changed_file_reingests_without_duplicating_existing_ideas(self):
        run_ingest(self.config, today="2026-02-01")
        # append a brand-new idea to the file; the 3 existing ideas stay identical
        app = self.src / "northwind-senior-pm" / "application_output.md"
        app.write_text(app.read_text(encoding="utf-8") +
                       "4. A genuinely new idea about pricing pages.\n", encoding="utf-8")
        summary = run_ingest(self.config, today="2026-02-03")
        self.assertEqual(summary.ideas_added, 1)          # only the new one
        self.assertEqual(summary.exact_dupes_skipped, 3)  # the 3 unchanged ideas prevented
        self.assertEqual(len(self._lib().ideas), 4)

    def test_exact_duplicate_prevented_near_duplicate_flagged(self):
        lib = self._lib()
        lib.add_idea("Pricing legibility", "Why pricing pages should explain themselves.",
                     today="2026-01-01")
        lib.save()
        # exact same premise -> prevented
        self.assertEqual(lib.find_matching_idea(
            "Pricing legibility", "Why pricing pages should explain themselves.")[1], "exact")
        # a close variant -> near
        _id, kind = lib.find_matching_idea(
            "Pricing clarity", "Why pricing pages should explain themselves clearly.")
        self.assertEqual(kind, "near")

    def test_ledger_persists_hashes(self):
        run_ingest(self.config, today="2026-02-01")
        led = IngestLedger.open(self.config["chain_home"])
        self.assertTrue(led.rows)
        self.assertTrue(all(r["sha256"] for r in led.rows))


if __name__ == "__main__":
    unittest.main()
