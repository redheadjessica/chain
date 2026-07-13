"""Public/private path-safety firewall (privacy boundary).

CHAIN owns two writable roots, chain_home and the review root
(__READY_TO_REVIEW__PRIVATE_GITIGNORED/). Each must resolve outside the repo, or
inside it only under a gitignored prefix.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chain.path_safety import check_writable_paths, path_is_git_safe  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


class TestPathSafety(unittest.TestCase):
    def test_outside_repo_is_safe(self):
        self.assertTrue(path_is_git_safe("~/.chain", REPO))
        self.assertTrue(path_is_git_safe("/tmp/chain-home", REPO))

    def test_gitignored_prefix_inside_repo_is_safe(self):
        self.assertTrue(path_is_git_safe(REPO / ".chain" / "demo-home", REPO))
        self.assertTrue(path_is_git_safe(REPO / "__READY_TO_REVIEW__PRIVATE_GITIGNORED", REPO))

    def test_unignored_path_inside_repo_is_unsafe(self):
        self.assertFalse(path_is_git_safe(REPO / "chain" / "leaky-home", REPO))
        self.assertFalse(path_is_git_safe(REPO / "docs" / "secrets", REPO))
        # examples/ is committed on purpose, so it is NOT a safe writable root
        self.assertFalse(path_is_git_safe(REPO / "examples" / "demo-home", REPO))

    def test_check_writable_paths_reports_the_leak(self):
        problems = check_writable_paths(
            {"chain_home": str(REPO / "canon" / "home")}, REPO  # unsafe
        )
        self.assertEqual({p.name for p in problems}, {"chain_home"})
        self.assertEqual(check_writable_paths({"chain_home": "~/.chain"}, REPO), [])

    def test_check_writable_paths_covers_the_review_root(self):
        problems = check_writable_paths(
            {"workspace_dir": str(REPO / "docs" / "leaky-workspace")}, REPO  # unsafe
        )
        self.assertEqual({p.name for p in problems}, {"workspace_dir"})
        self.assertEqual(
            check_writable_paths(
                {"workspace_dir": str(REPO / "__READY_TO_REVIEW__PRIVATE_GITIGNORED")}, REPO
            ),
            [],
        )

    def test_gitignore_covers_the_firewall(self):
        gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".chain/", gitignore)
        self.assertIn("PRIVATE__YOUR_FILES_GITIGNORED/", gitignore)
        self.assertIn("__READY_TO_REVIEW__PRIVATE_GITIGNORED/", gitignore)
        self.assertIn("*.config.local.yaml", gitignore)

    def test_demo_home_is_the_committed_seed(self):
        """The synthetic demo home is committed on purpose so the repo runs; assert
        its library seed exists and lives under examples/."""
        lib = REPO / "examples" / "demo-home" / "library"
        self.assertTrue((lib / "ideas.csv").exists())
        self.assertTrue((lib / "pieces.csv").exists())


if __name__ == "__main__":
    unittest.main()
