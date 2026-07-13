# Intake personas (synthetic)

Three committed test personas covering the intake maturity model — no private data.
Each has a config; run the deterministic intake against any of them, from the repo
root (paths are relative to `ENGINE__PUBLIC_GIT_TRACKED/`, where `./chain` runs
commands from):

    ./chain intake examples/intake-personas/p1-organized.config.yaml

| Persona | Level | Proves |
|---|---|---|
| `p1-organized` (Maya Chen, coach) | 1 | existing corpus + voice + pillars are validated and mapped in place; nothing recreated; only optional gaps remain |
| `p2-studio` (Sweet Fern Studio, reuses `examples/demo-sources-studio/`) | 2 | scattered FAQs/reviews/notes classify into a source map; missing guidance is distilled FROM the material |
| `p3-newcomer` (Dr. Sam Okafor, researcher) | 3 | intake creates a usable starting point via interview + writing exercises rather than reporting missing files |

The collaborative halves of levels 2-3 are exercised by the `chain-intake` agent (see
`.claude/agents/chain-intake.md` at the repo root, and this directory's sibling
`canon/intake-interview-guide.md`); the deterministic classification, maturity, plan,
and manifest behavior for all three is covered by `tests/test_intake.py`.
