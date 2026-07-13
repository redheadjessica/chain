# CHAIN — Privacy Boundary

CHAIN is public-first. The repository ships the **mechanism**; your data never has to
enter git. This page is the contract.

## Three locations, one firewall

CHAIN distinguishes **your world** (referenced in place, read-only), **`chain_home`**
(machine state plus the durable library it owns), and the **review root**
(`__READY_TO_REVIEW__PRIVATE_GITIGNORED/`, generated output waiting on you). Everything
private is one of the three, and none of them are committed.

| Committed (public-safe) | Never committed |
|---|---|
| Engine code, connectors, lint, schemas | `chain.config.local.yaml` (your real paths) |
| Agent definitions, workflow, run presets | **Your sources** (writing, applications, repos) — referenced in place |
| `canon/…template.md` (generic templates) | **Your canon** (voice spec, pillars) — referenced in place |
| `examples/` synthetic persona + demo config | **`chain_home/`** (library, learned state, cache) |
| Docs, tests (synthetic fixtures only) | **`__READY_TO_REVIEW__PRIVATE_GITIGNORED/`** (drafts, packets), cache, analytics, credentials, sessions |

## What must never be committed

Private job applications · unpublished writing · personal LinkedIn exports · private
analytics · user-specific style feedback · generated drafts based on private source
material · credentials or local session data.

## How it's enforced

1. **`.gitignore`** covers `chain.config.local.yaml`, `.chain/` (the default and demo
   location of `chain_home`), and `__READY_TO_REVIEW__PRIVATE_GITIGNORED/` (the review
   root), plus credential patterns.
2. **CHAIN writes only to `chain_home` and the review root.** Your sources and canon
   are read-only and mapped in place — never copied into a permanent CHAIN location
   (single source of truth). The one exception is generated output itself, which CHAIN
   originates rather than references, and whose canonical home is the review root, not
   a disposable scratch folder. The ingestion ledger and cache hold references,
   hashes, metadata, narrow excerpts, and normalized indexes — never full copies of
   your files.
3. **A runtime check** ([`chain/path_safety.py`](../chain/path_safety.py)) and the
   test-suite refuse any writable root — `chain_home` or the review root — that
   resolves inside the repo without being gitignored. `config.load_config()` raises
   before a run rather than risk a leak.

## Adapt to your world

CHAIN never asks you to move your writing into a CHAIN folder. You point it at the
folders you already have. The only thing that must live in `chain_home` is the state
CHAIN itself authors (your ideas, the pieces index, learned feedback) — because that
doesn't exist anywhere in your world yet.

## The demo persona

`examples/demo-home/` is a **synthetic** persona ("Alex Rivera"), committed on purpose
so the repo runs end-to-end with zero private data. It is a *seed*: copy it into a
gitignored `chain_home` before a demo run. The path-safety test asserts it is not
itself usable as a live writable root.
