#!/usr/bin/env python3
"""CHAIN changelog synthesis.

The changelog is edited as human-readable project history, not compressed by age or
forced into one entry per day. Granular entries (added by a human or a coding agent
during normal work) are the primary source; Git history is supporting evidence for
verification and filling genuine gaps. Stdlib-only, like `path_safety.py` and
`editorial_library.py` — no new runtime dependency for repo self-maintenance.

Usage:
    python3 -m chain.changelog_sync --mark-current   # establish a safe baseline
    python3 -m chain.changelog_sync --normalize-only  # structure check, no AI call
    python3 -m chain.changelog_sync --dry-run         # AI pass, no writes
    python3 -m chain.changelog_sync                   # live AI pass
    python3 -m chain.changelog_sync --force           # force a pass with no meaningful diff
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from .changelog_core import (
    get_processed_commit,
    meaningful_changed_files,
    normalize_changelog,
    set_processed_commit,
)
from .config import REPO_ROOT

DOCS_DIR = REPO_ROOT / "docs"

PATHS = {
    "changelog": DOCS_DIR / "changelog.md",
    "architecture": DOCS_DIR / "architecture.md",
    "readme": REPO_ROOT / "README.md",
    "doc_status": DOCS_DIR / "doc-status.md",
}


def load_env() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf8").splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip("\"'")


def read_doc(path: Path):
    return path.read_text(encoding="utf8") if path.exists() else None


def write_doc(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry run] Would write {path.relative_to(REPO_ROOT)} ({content.count(chr(10)) + 1} lines)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf8")
    print(f"✓ Wrote {path.relative_to(REPO_ROOT)}")


def run_git(args: list) -> str:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def current_commit() -> str:
    return run_git(["rev-parse", "HEAD"])


def ensure_commit_exists(commit: str) -> None:
    try:
        run_git(["cat-file", "-e", f"{commit}^{{commit}}"])
    except subprocess.CalledProcessError:
        raise RuntimeError(
            f"The changelog marker points to {commit}, which is not available in this "
            "Git history. Run with --mark-current to establish a new baseline."
        )


def collect_git_evidence(base_commit: str, head_commit: str) -> dict:
    ensure_commit_exists(base_commit)
    rng = f"{base_commit}..{head_commit}"
    files = [f for f in run_git(["diff", "--name-only", rng]).splitlines() if f]
    meaningful_files = meaningful_changed_files(files)

    log = ""
    if meaningful_files:
        log = run_git(
            [
                "log",
                "--date=short",
                "--format=commit %H%nDate: %ad%nSubject: %s",
                "--name-status",
                rng,
                "--",
                *meaningful_files,
            ]
        )

    diff = ""
    if meaningful_files:
        diff = run_git(["diff", "--unified=1", rng, "--", *meaningful_files])

    return {
        "base_commit": base_commit,
        "head_commit": head_commit,
        "files": files,
        "meaningful_files": meaningful_files,
        "log": log[:16_000],
        "diff": diff[:28_000],
    }


def call_claude(system_prompt: str, user_message: str, verbose: bool) -> str:
    import urllib.error
    import urllib.request

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required for an AI synthesis pass.")

    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
    if verbose:
        print(f"Claude model: {model}")
        print(f"Prompt sizes: system={len(system_prompt)}, user={len(user_message)}")

    payload = json.dumps(
        {
            "model": model,
            "max_tokens": 8192,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }
    ).encode("utf8")

    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode("utf8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Claude API error {error.code}: {error.read().decode('utf8')}")

    for block in data.get("content", []):
        if block.get("type") == "text":
            return block.get("text", "")
    return ""


def strip_markdown_fence(value: str) -> str:
    value = value.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1] if "\n" in value else ""
    if value.endswith("```"):
        value = value.rsplit("```", 1)[0]
    return value.strip()


def rewrite_changelog(changelog: str, evidence: dict, verbose: bool) -> str:
    system = """You edit CHAIN's changelog as interesting, human-readable project history.

CHAIN is a channel-neutral editorial engine: it discovers or develops ideas from a
person's own writing and takes them through a shared Draft -> Evaluate -> Finalize
spine into a finished piece. It prepares; the person publishes. Design principles:
adapt to the user's world (never move their files), single source of truth (index
and reference, don't copy), minimize cognitive overhead (fewest durable concepts).

Editorial rules:
- Organize around meaningful change threads: a feature may span multiple days, and one
  day may contain several distinct entries.
- Use "## YYYY-MM-DD — Title" for one day.
- Use "## YYYY-MM-DD to DD — Title" for a range within one month.
- Use both full dates for a range crossing a month or year.
- There is no fixed bullet count. Use as many as the story warrants, usually 1-8, but
  every bullet must add meaningful information.
- Preserve: what changed and why, the user problem/testing result/confusion/failure
  that prompted it, privacy/trust/provenance/control concerns (CHAIN's privacy
  firewall around chain_home, source-mapping-in-place rather than copying), important
  architectural simplifications, decisions to remove complexity, cases where actual
  use contradicted the initial design, meaningful changes in how the human and the
  writer/evaluator agents interact, and explorations that produced a useful
  conclusion even when they did not directly ship.
- Describe the lasting outcome rather than narrating every intermediate attempt.
- Drop routine test counts, file inventories, debug fields, tiny polish iterations,
  and superseded implementation attempts that later work replaced.
- Granular changelog entries are the primary account. Use Git evidence to verify
  claims and fill genuine gaps, not to turn the changelog into a commit log.
- Keep the historical "Pre-history" and "Earlier" sections intact unless new evidence
  directly corrects them.
- Treat the result as public: omit secrets, credentials, API keys, or any real
  person's private material referenced during development.
- Preserve the document preamble and the hidden changelog-processed-through marker.
- Return the complete Markdown document only, without a code fence or explanation."""

    user = f"""Current curated changelog:
<changelog>
{changelog}
</changelog>

Git evidence since {evidence['base_commit']}:
<commit_log>
{evidence['log'] or 'No commit messages in range.'}
</commit_log>

Meaningful changed files:
{chr(10).join(evidence['meaningful_files']) or 'None'}

Supporting diff excerpt (may be truncated):
<diff>
{evidence['diff'] or 'No meaningful product diff in range.'}
</diff>

Update only what the new work warrants. Preserve already-curated older history."""

    return strip_markdown_fence(call_claude(system, user, verbose))


def update_architecture_doc(changelog: str, existing_architecture, verbose: bool):
    today = date.today().isoformat()
    system = f"""Update CHAIN's architecture reference (docs/architecture.md) from its
curated changelog. Describe current reality: the design principles, the chain_home
model, the Discover/Directed entry modes, the Draft -> Evaluate -> Finalize spine, and
what is live, partial, or exploratory. Correct superseded information, but do not
invent modules, stages, or concepts that the changelog does not support. Keep the
document's existing structure and section headers where still accurate. Return the
complete Markdown document only, without a code fence or explanation. Note {today} as
the freshness point only if the document already tracks one."""
    user = f"""Existing architecture doc:
{existing_architecture if existing_architecture is not None else "(Not available -- report that no current-state doc exists rather than inventing one.)"}

Curated changelog:
{changelog}"""
    return strip_markdown_fence(call_claude(system, user, verbose))


def check_for_drift(changelog: str, readme, verbose: bool):
    today = date.today().isoformat()
    system = f"""Check README.md's "Status" section and core-concepts description
against CHAIN's curated changelog. Report only concrete discrepancies. Absence from
the changelog is not proof of drift. Use this Markdown structure:
## Drift Report — {today}
### README.md
- ...
### Recommended actions
- ..."""
    user = f"""Curated changelog:
{changelog}

README.md:
{readme if readme is not None else "(Not available.)"}"""
    return strip_markdown_fence(call_claude(system, user, verbose))


def build_doc_status(drift_report: str) -> str:
    today = date.today().isoformat()
    return f"""# CHAIN — Doc Status

> Last synthesis pass: {today}
> Run `python3 -m chain.changelog_sync` to refresh.

## Last Drift Report

{drift_report}
"""


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="CHAIN changelog synthesis")
    ap.add_argument("--mark-current", action="store_true", help="establish a safe baseline")
    ap.add_argument("--normalize-only", action="store_true", help="structure check, no AI call")
    ap.add_argument("--dry-run", action="store_true", help="AI pass, no writes")
    ap.add_argument("--force", action="store_true", help="force a pass with no meaningful diff")
    ap.add_argument("--verbose", action="store_true", help="show prompt sizes and model used")
    args = ap.parse_args(argv)

    load_env()
    changelog = read_doc(PATHS["changelog"])
    if changelog is None:
        raise RuntimeError("docs/changelog.md was not found.")

    normalized = normalize_changelog(changelog)
    head_commit = current_commit()

    if args.mark_current:
        write_doc(PATHS["changelog"], normalize_changelog(set_processed_commit(normalized, head_commit)), args.dry_run)
        print(f"✓ Changelog baseline set to {head_commit[:12]}")
        return 0

    if args.normalize_only:
        if normalized == changelog:
            print("✓ Changelog structure is normalized; no changes needed.")
        else:
            write_doc(PATHS["changelog"], normalized, args.dry_run)
        return 0

    base_commit = get_processed_commit(changelog)
    if not base_commit:
        raise RuntimeError(
            "No changelog baseline marker exists. Review the current changelog, then "
            "run with --mark-current once."
        )

    evidence = collect_git_evidence(base_commit, head_commit)
    if not args.force and not evidence["meaningful_files"]:
        if normalized != changelog:
            write_doc(PATHS["changelog"], normalized, args.dry_run)
        print("✓ No new editorial, exploration, or documentation changes to synthesize.")
        return 0

    print(
        f"→ Synthesizing {len(evidence['meaningful_files'])} meaningful changed file(s) "
        f"from {base_commit[:12]} to {head_commit[:12]}..."
    )

    rewritten = rewrite_changelog(normalized, evidence, args.verbose)
    new_changelog = normalize_changelog(set_processed_commit(rewritten, head_commit))
    existing_architecture = read_doc(PATHS["architecture"])
    readme = read_doc(PATHS["readme"])

    updated_architecture = update_architecture_doc(new_changelog, existing_architecture, args.verbose)
    drift_report = check_for_drift(new_changelog, readme, args.verbose)

    write_doc(PATHS["changelog"], new_changelog, args.dry_run)
    if existing_architecture is not None:
        write_doc(PATHS["architecture"], updated_architecture, args.dry_run)
    write_doc(PATHS["doc_status"], build_doc_status(drift_report), args.dry_run)
    print("✓ Dry run complete; no files were changed." if args.dry_run else "✓ Documentation synthesis complete.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001
        print(f"✗ Synthesis failed: {error}", file=sys.stderr)
        sys.exit(1)
