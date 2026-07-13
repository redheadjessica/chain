#!/usr/bin/env python3
"""Path-safety checks — the runtime half of the privacy firewall.

CHAIN has two writable roots: `chain_home` (default ~/.chain — machine state and the
durable library) and the review root (fixed: __READY_TO_REVIEW__PRIVATE_GITIGNORED/,
where generated output waits for human review). Each must resolve OUTSIDE the
repository, or (if kept local, e.g. for the demo) under a gitignored prefix such as
`.chain/`. This lets a preflight (`chain doctor`) and the test-suite assert that CHAIN
can never leak private data into git.

A writable root is SAFE when either:
  * it resolves outside the repository tree, or
  * it is inside the repo but under a gitignored prefix.

Your canon references (voice_spec, positioning_pillars) and your sources are
read-only inputs mapped in place — they are not checked here because CHAIN never
writes to them.

Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Repo-relative prefixes that .gitignore keeps out of git and that CHAIN may write
# into: `.chain/` when chain_home is kept local (default ~/.chain lives outside the
# repo), and the review root, which lives in-repo by default.
IGNORED_WRITABLE_PREFIXES = (".chain", "__READY_TO_REVIEW__PRIVATE_GITIGNORED")


@dataclass(frozen=True)
class PathProblem:
    name: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"[unsafe path] {self.name} -> {self.path}: {self.message}"


def _resolve(p) -> Path:
    return Path(p).expanduser().resolve()


def is_within(path, root) -> bool:
    """True if `path` is inside `root` (both resolved)."""
    path, root = _resolve(path), _resolve(root)
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def path_is_git_safe(path, repo_root, ignored_prefixes=IGNORED_WRITABLE_PREFIXES) -> bool:
    """A writable path is safe if it is outside the repo, or inside it only under a
    gitignored writable prefix."""
    if not is_within(path, repo_root):
        return True  # outside the repo entirely — nothing can be committed
    rel = _resolve(path).relative_to(_resolve(repo_root))
    top = rel.parts[0] if rel.parts else ""
    return top in ignored_prefixes


def check_writable_paths(paths: dict, repo_root, ignored_prefixes=IGNORED_WRITABLE_PREFIXES):
    """`paths` maps a name (e.g. 'chain_home') to a filesystem path. Returns a list
    of PathProblem for any writable path that could leak into git."""
    problems = []
    for name, p in paths.items():
        if not p:
            continue
        if not path_is_git_safe(p, repo_root, ignored_prefixes):
            problems.append(PathProblem(
                name, str(p),
                "resolves inside the repo but is not under a gitignored prefix "
                f"({', '.join(ignored_prefixes)}) — move it outside the repo or into ~/.chain",
            ))
    return problems
