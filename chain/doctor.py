#!/usr/bin/env python3
"""`chain doctor` — preflight that fails loud before a run can go wrong.

Deterministic checks only:
  * the privacy firewall (chain_home safe),
  * the editorial library is valid (ID integrity + no orphaned references),
  * the ingestion ledger loads,
  * each configured source path exists (missing = warn, not fatal),
  * the canon references (voice_spec, positioning_pillars) exist (warn).

Reports errors and warnings; exit non-zero if any error. Stdlib only (except the
optional yaml used to read a config file at the CLI boundary).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .editorial_library import EditorialLibrary
from .ingest import IngestLedger
from .path_safety import check_writable_paths


@dataclass(frozen=True)
class Check:
    status: str   # "ok" | "warn" | "error"
    name: str
    detail: str

    def __str__(self) -> str:
        icon = {"ok": "ok  ", "warn": "warn", "error": "ERR "}[self.status]
        return f"[{icon}] {self.name}: {self.detail}"


def run_doctor(config: dict, repo_root) -> list:
    checks: list = []

    # 1. privacy firewall
    chain_home = config.get("chain_home", "")
    problems = check_writable_paths({"chain_home": chain_home}, repo_root)
    if problems:
        checks.append(Check("error", "firewall", str(problems[0])))
    else:
        checks.append(Check("ok", "firewall", f"chain_home safe ({chain_home})"))

    # 2. editorial library
    lib_dir = Path(config.get("library_dir", Path(chain_home) / "library"))
    if not (lib_dir / "ideas.csv").exists():
        checks.append(Check("warn", "library", f"no ideas.csv yet at {lib_dir} (fresh home)"))
    else:
        lib = EditorialLibrary.open(lib_dir)
        errs = [p for p in lib.validate() if p.severity == "error"]
        if errs:
            checks.append(Check("error", "library", f"{len(errs)} integrity error(s): {errs[0]}"))
        else:
            checks.append(Check("ok", "library",
                                f"{len(lib.ideas)} ideas, {len(lib.pieces)} pieces, valid"))

    # 3. ingestion ledger
    try:
        led = IngestLedger.open(chain_home)
        checks.append(Check("ok", "ledger", f"{len(led.rows)} tracked file(s)"))
    except Exception as exc:  # pragma: no cover - defensive
        checks.append(Check("error", "ledger", f"cannot read ledger: {exc}"))

    # 4. sources exist
    for sd in config.get("sources", []):
        if not sd.get("enabled", True):
            continue
        p = Path(str(sd.get("path", ""))).expanduser()
        if p.exists():
            checks.append(Check("ok", f"source:{sd.get('name')}", str(p)))
        else:
            checks.append(Check("warn", f"source:{sd.get('name')}", f"path not found: {p}"))

    # 5. canon references
    for key in ("voice_spec", "positioning_pillars"):
        ref = config.get(key)
        if not ref:
            checks.append(Check("warn", key, "not configured"))
        elif Path(str(ref)).expanduser().exists():
            checks.append(Check("ok", key, str(ref)))
        else:
            checks.append(Check("warn", key, f"not found: {ref}"))

    return checks


def main(argv=None):
    import argparse
    from .config import REPO_ROOT, load_config
    ap = argparse.ArgumentParser(description="CHAIN preflight")
    ap.add_argument("config", nargs="?", help="path to a config yaml (default: local)")
    args = ap.parse_args(argv)
    cfg = load_config(local_path=args.config) if args.config else load_config()
    checks = run_doctor(cfg, REPO_ROOT)
    for c in checks:
        print(c)
    errors = [c for c in checks if c.status == "error"]
    warns = [c for c in checks if c.status == "warn"]
    print(f"=> {len(errors)} error(s), {len(warns)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
