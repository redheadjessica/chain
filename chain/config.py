#!/usr/bin/env python3
"""Configuration loading for CHAIN.

Loads the committed example as defaults and overlays your gitignored local copy,
expands `~` and `{chain_home}` placeholders, and validates that the one writable
root (chain_home) is safe (path_safety). PyYAML is the single runtime dependency;
the editorial-library helper and path-safety checks are stdlib-only so they run
(and are tested) without any install.

Location model (see docs/architecture.md):
  * chain_home            — the one writable root CHAIN owns (default ~/.chain).
                            library/ and workspace/ live inside it.
  * voice_spec,           — read-only canon REFERENCES; point them at files you
    positioning_pillars     already have, anywhere. Never relocated or copied.
  * sources               — your existing folders, mapped in place.
"""

from __future__ import annotations

from pathlib import Path

from .path_safety import check_writable_paths

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_CONFIG = REPO_ROOT / "chain.config.example.yaml"
LOCAL_CONFIG = REPO_ROOT / "PRIVATE__YOUR_FILES_GITIGNORED" / "chain.config.local.yaml"


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "CHAIN config needs PyYAML.  pip install pyyaml  (or: python -m pip install pyyaml)"
        ) from exc
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _expand(value, ctx):
    if isinstance(value, str):
        out = value.format(**ctx) if "{" in value else value
        return str(Path(out).expanduser()) if out.startswith("~") else out
    if isinstance(value, list):
        return [_expand(v, ctx) for v in value]
    if isinstance(value, dict):
        return {k: _expand(v, ctx) for k, v in value.items()}
    return value


def load_config(local_path=None, example_path=None, *, check_paths=True) -> dict:
    example_path = Path(example_path or EXAMPLE_CONFIG)
    local_path = Path(local_path or LOCAL_CONFIG)

    cfg = _load_yaml(example_path)
    if local_path.exists():
        cfg.update({k: v for k, v in _load_yaml(local_path).items() if v is not None})

    # Resolve the one writable root first so everything else can reference it.
    chain_home = str(Path(str(cfg.get("chain_home", "~/.chain"))).expanduser())
    ctx = {"chain_home": chain_home}
    cfg = _expand(cfg, ctx)
    cfg["chain_home"] = chain_home
    # Derived, not separately configured (fewer config surfaces):
    cfg["library_dir"] = str(Path(chain_home) / "library")
    cfg["workspace_dir"] = str(Path(chain_home) / "workspace")

    if check_paths:
        problems = check_writable_paths({"chain_home": chain_home}, REPO_ROOT)
        if problems:
            raise SystemExit(
                "Refusing to run: chain_home could leak into git.\n  "
                + "\n  ".join(str(p) for p in problems)
            )
    return cfg
