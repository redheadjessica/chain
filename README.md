# CHAIN

**Contextual Human-AI Narrative System** — a channel-neutral editorial engine that
turns the writing you've *already done* into new public work.

> If creating every post by hand leaves you chained to your desk, CHAIN helps you get
> out. It discovers ideas from your own material, drafts and critiques them, and hands
> you a publish-ready packet with an honest verdict. **It prepares — you publish.**
> CHAIN never posts on your behalf.

CHAIN reads your source libraries **where they already live** and finds ideas worth
writing, then takes each through a shared **Draft → Evaluate → Finalize** spine into a
finished piece for any channel — a short post, a Medium article, a companion post, a
website essay. It's **domain-agnostic**: the sources might be a product person's essays
and project notes, or a sugaring studio's FAQs, reviews, and consultation notes. Same
engine, same lenses, your voice.

## Design principles

1. **Adapt to your world** — never reorganize your folders; CHAIN maps them in place.
2. **Single source of truth** — index and reference existing material, don't copy it.
3. **Minimize cognitive overhead** — the fewest durable concepts that support a
   powerful workflow.

See [docs/architecture.md](docs/architecture.md#design-principles).

## Core concepts

- **Idea** — a possible premise or direction. One idea can produce several pieces of
  work over time.
- **Draft** — an unpublished expression of an idea.
- **Published writing** — the final public work, wherever its canonical text or URL
  already lives.

"Writing" always means *published* work; unfinished work is a **Draft**. Internally
these are rows in two human-editable CSVs under your `chain_home` (default `~/.chain`),
the one writable location CHAIN owns; Drafts and Published writing are status views of
the same rows.

## How it works

- **Two entry modes.** *Discover* synthesizes ideas from your sources autonomously;
  *Directed* develops a specific input you hand it.
- **One writer, one evaluator, one deterministic linter.** Lint checks mechanical
  compliance; the evaluator handles judgment and writes a candid publish verdict.
- **Positioning over popularity.** Pieces are judged on the professional impression
  they build, not on predicted engagement.

## Status

**Early (v0.0.1).** In place: the privacy firewall, config pattern, editorial library,
idempotent source intake + idea harvesting, the domain-agnostic Discover synthesis
(portable `chain-discoverer`), and the production spine **Brief → Draft → Evaluate →
bounded Finalize** (portable `chain-writer` / `chain-evaluator`, deterministic
`lint_draft`, private draft packets). Validated across two domains (a product persona and
a sugaring studio). Next: long-form + companion **bundles**, then the five-output
autonomous run. See [docs/architecture.md](docs/architecture.md).

## Quickstart

```bash
git clone <this repo> && cd chain
cp chain.config.example.yaml chain.config.local.yaml   # point paths at your folders
python3 -m unittest discover -s tests                  # runs with zero installs
python3 -m chain.editorial_library validate examples/demo-home/library
```

The `examples/` synthetic persona lets you see the data model with **no private data**.

## Docs

- [Architecture](docs/architecture.md) · [Future work](docs/future-work.md)
- [Sources](docs/sources.md) · [Privacy](docs/privacy.md) · [The packet](docs/packet.md)

## License

MIT — see [LICENSE](LICENSE).
