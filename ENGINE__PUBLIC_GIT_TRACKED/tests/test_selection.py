"""Selection traceability: an append-only, honest record of why an idea moved into
production — never a re-ranking, never invented after the fact."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.selection import (as_packet_selection, latest_selection_for,  # noqa: E402
                             load_selection_log, log_path, record_selection)


class TestSelection(unittest.TestCase):
    def _config(self):
        return {"chain_home": str(Path(tempfile.mkdtemp()))}

    def test_record_and_reload_roundtrip(self):
        cfg = self._config()
        record_selection(cfg, selected_idea_id="IDEA-0003",
                         candidates=["IDEA-0001", "IDEA-0002", "IDEA-0003"],
                         mechanism="user-directed", ranking_type="manual",
                         factors="strongest engagement evidence", today="2026-07-12")
        log = load_selection_log(cfg)
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["selected_idea_id"], "IDEA-0003")
        self.assertEqual(log[0]["candidates"], ["IDEA-0001", "IDEA-0002", "IDEA-0003"])
        self.assertTrue(log_path(cfg).exists())

    def test_append_only_accumulates(self):
        cfg = self._config()
        record_selection(cfg, selected_idea_id="IDEA-0001", candidates=["IDEA-0001"],
                         mechanism="automatic", ranking_type="quality", today="2026-07-11")
        record_selection(cfg, selected_idea_id="IDEA-0002", candidates=["IDEA-0002"],
                         mechanism="automatic", ranking_type="quality", today="2026-07-12")
        self.assertEqual(len(load_selection_log(cfg)), 2)

    def test_latest_selection_for_idea(self):
        cfg = self._config()
        record_selection(cfg, selected_idea_id="IDEA-0003", candidates=["IDEA-0003"],
                         mechanism="automatic", ranking_type="quality", today="2026-07-11")
        record_selection(cfg, selected_idea_id="IDEA-0003", candidates=["IDEA-0003", "IDEA-0004"],
                         mechanism="user-directed", ranking_type="manual", today="2026-07-12")
        latest = latest_selection_for(cfg, "IDEA-0003")
        self.assertEqual(latest["mechanism"], "user-directed")

    def test_no_selection_recorded_returns_none_honestly(self):
        cfg = self._config()
        self.assertIsNone(latest_selection_for(cfg, "IDEA-9999"))
        packet_sel = as_packet_selection(None)
        self.assertEqual(packet_sel["mechanism"], "not recorded")
        self.assertIn("no selection event was logged", packet_sel["note"])

    def test_invalid_mechanism_rejected(self):
        cfg = self._config()
        with self.assertRaises(ValueError):
            record_selection(cfg, selected_idea_id="IDEA-0001", candidates=["IDEA-0001"],
                             mechanism="telepathy", ranking_type="quality")

    def test_as_packet_selection_shapes_record(self):
        record = {"mechanism": "manual-test", "ranking_type": "manual",
                  "factors": "richest existing draft material", "note": "extra context"}
        out = as_packet_selection(record)
        self.assertIn("manually", out["mechanism"])
        self.assertIn("richest existing draft material", out["note"])
        self.assertIn("extra context", out["note"])


if __name__ == "__main__":
    unittest.main()
