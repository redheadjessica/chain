"""ID minting + integrity, and lightweight manual entry."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.editorial_library import EditorialLibrary  # noqa: E402


class TestIdIntegrity(unittest.TestCase):
    def _lib(self):
        d = Path(tempfile.mkdtemp())
        return EditorialLibrary(d / "ideas.csv", d / "pieces.csv")

    def test_mint_is_monotonic_and_zero_padded(self):
        lib = self._lib()
        first = lib.add_idea("Title one", "A premise.", today="2026-01-01")
        second = lib.add_idea("Title two", "Another premise.", today="2026-01-01")
        self.assertEqual(first, "IDEA-0001")
        self.assertEqual(second, "IDEA-0002")

    def test_piece_ids_independent_sequence(self):
        lib = self._lib()
        iid = lib.add_idea("Idea", "Premise.", today="2026-01-01")
        p1 = lib.add_piece(iid, fmt="long_form", channel="medium")
        p2 = lib.add_piece(iid, fmt="short_form", channel="linkedin",
                           relation_type="companion-of")
        self.assertEqual((p1, p2), ("PIECE-0001", "PIECE-0002"))

    def test_minimal_manual_entry_is_valid(self):
        """A working_title + premise is a complete idea; the rest defaults."""
        lib = self._lib()
        iid = lib.add_idea("Just a title", "Just a rough premise.", today="2026-01-01")
        idea = lib.get_idea(iid)
        self.assertEqual(idea["status"], "proposed")
        self.assertEqual(idea["date_added"], "2026-01-01")
        self.assertTrue(lib.is_valid())

    def test_missing_required_fields_rejected(self):
        lib = self._lib()
        with self.assertRaises(ValueError):
            lib.add_idea("", "no title")
        with self.assertRaises(ValueError):
            lib.add_idea("no premise", "")

    def test_draft_and_published_are_views_of_pieces(self):
        """Drafts and published are the same object at different statuses."""
        lib = self._lib()
        iid = lib.add_idea("Idea", "Premise.", today="2026-01-01")
        d = lib.add_piece(iid, fmt="short_form", channel="linkedin", status="draft")
        lib.add_piece(iid, fmt="long_form", channel="medium", status="published")
        self.assertEqual([p["piece_id"] for p in lib.drafts()], [d])
        self.assertEqual(len(lib.published()), 1)

    def test_groom_assigns_ids_to_handwritten_rows(self):
        lib = self._lib()
        lib.ideas.append({"working_title": "Hand added", "premise": "By hand."})
        changes = lib.groom(today="2026-02-02")
        self.assertTrue(any("IDEA-0001" in c for c in changes))
        self.assertTrue(lib.is_valid())

    def test_roundtrip_save_and_reopen(self):
        lib = self._lib()
        iid = lib.add_idea("Persisted", "Premise.", today="2026-01-01")
        pid = lib.add_piece(iid, fmt="short_form", channel="linkedin")
        lib.save()
        reopened = EditorialLibrary(lib.ideas_path, lib.pieces_path)
        self.assertIsNotNone(reopened.get_idea(iid))
        self.assertEqual([p["piece_id"] for p in reopened.pieces_for_idea(iid)], [pid])


if __name__ == "__main__":
    unittest.main()
