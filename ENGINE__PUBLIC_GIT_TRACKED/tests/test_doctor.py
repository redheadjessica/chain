"""chain doctor preflight checks."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.doctor import run_doctor  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


class TestDoctor(unittest.TestCase):
    def _statuses(self, checks, name):
        return [c.status for c in checks if c.name == name]

    def test_safe_fresh_home_has_no_errors(self):
        home = Path(tempfile.mkdtemp())
        config = {
            "chain_home": str(home),
            "library_dir": str(home / "library"),
            "sources": [],
        }
        checks = run_doctor(config, REPO)
        self.assertEqual([c for c in checks if c.status == "error"], [])
        self.assertEqual(self._statuses(checks, "firewall"), ["ok"])

    def test_leaky_chain_home_is_an_error(self):
        config = {
            "chain_home": str(REPO / "canon" / "leaky"),  # inside repo, unignored
            "library_dir": str(REPO / "canon" / "leaky" / "library"),
            "sources": [],
        }
        checks = run_doctor(config, REPO)
        self.assertEqual(self._statuses(checks, "firewall"), ["error"])

    def test_missing_source_path_warns_not_errors(self):
        home = Path(tempfile.mkdtemp())
        config = {
            "chain_home": str(home),
            "library_dir": str(home / "library"),
            "sources": [{"name": "linkedin", "type": "linkedin_posts",
                         "path": "/no/such/place", "enabled": True}],
        }
        checks = run_doctor(config, REPO)
        self.assertEqual([c for c in checks if c.status == "error"], [])
        self.assertIn("warn", self._statuses(checks, "source:linkedin"))


if __name__ == "__main__":
    unittest.main()
