"""Orphaned-reference detection and the derived idea->pieces relationship."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.editorial_library import EditorialLibrary  # noqa: E402


class TestOrphanedReferences(unittest.TestCase):
    def _lib(self):
        d = Path(tempfile.mkdtemp())
        return EditorialLibrary(d / "ideas.csv", d / "pieces.csv")

    def _codes(self, lib):
        return {p.code for p in lib.validate() if p.severity == "error"}

    def test_pieces_are_derived_not_stored(self):
        """One idea -> many pieces, discovered by filtering pieces.csv."""
        lib = self._lib()
        iid = lib.add_idea("Bundle idea", "Premise.", today="2026-01-01")
        art = lib.add_piece(iid, fmt="article", channel="medium")
        comp = lib.add_piece(iid, fmt="companion_post", channel="linkedin",
                             parent_piece_id=art, relation_type="companion-of")
        got = {p["piece_id"] for p in lib.pieces_for_idea(iid)}
        self.assertEqual(got, {art, comp})
        self.assertNotIn("piece_ids", lib.get_idea(iid))  # no reverse column at all

    def test_piece_with_unknown_idea_id_is_orphan(self):
        lib = self._lib()
        lib.pieces.append({"piece_id": "PIECE-0001", "idea_id": "IDEA-9999",
                           "format": "short_post", "channel": "linkedin",
                           "status": "draft"})
        self.assertIn("orphaned-reference", self._codes(lib))

    def test_dangling_parent_piece_is_orphan(self):
        lib = self._lib()
        iid = lib.add_idea("Idea", "Premise.", today="2026-01-01")
        lib.add_piece(iid, fmt="companion_post", channel="linkedin",
                      parent_piece_id="PIECE-4242", relation_type="companion-of")
        self.assertIn("orphaned-reference", self._codes(lib))

    def test_dangling_related_idea_is_orphan(self):
        lib = self._lib()
        lib.add_idea("Idea", "Premise.", today="2026-01-01",
                     related_idea_ids="IDEA-8888")
        self.assertIn("orphaned-reference", self._codes(lib))

    def test_multivalue_delimiter_is_pipe_not_comma(self):
        """Commas belong to free text; links use '|'."""
        lib = self._lib()
        a = lib.add_idea("A", "Premise a, with a comma.", today="2026-01-01")
        b = lib.add_idea("B", "Premise b.", today="2026-01-01")
        c = lib.add_idea("C", "Premise c.", today="2026-01-01")
        lib.get_idea(a)["related_idea_ids"] = f"{b}|{c}"
        self.assertTrue(lib.is_valid())
        lib.get_idea(a)["related_idea_ids"] = f"{b},{c}"  # comma = one bad id
        self.assertIn("orphaned-reference", self._codes(lib))

    def test_duplicate_ids_flagged(self):
        lib = self._lib()
        iid = lib.add_idea("Idea", "Premise.", today="2026-01-01")
        lib.ideas.append(dict(lib.get_idea(iid)))
        self.assertIn("duplicate-id", self._codes(lib))

    def test_clean_library_has_no_errors(self):
        lib = self._lib()
        iid = lib.add_idea("Idea", "Premise.", today="2026-01-01")
        art = lib.add_piece(iid, fmt="article", channel="medium")
        lib.add_piece(iid, fmt="companion_post", channel="linkedin",
                      parent_piece_id=art, relation_type="companion-of")
        self.assertEqual(self._codes(lib), set())


if __name__ == "__main__":
    unittest.main()
