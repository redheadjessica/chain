"""Adaptive intake: classification, maturity, plan, manifest, CLI, personas."""

import json
import tempfile
import unittest
from pathlib import Path

from chain.config import load_config
from chain.intake import (ASSETS, REGISTRY, build_manifest, build_plan, classify,
                          load_manifest, main, manifest_path, maturity_level,
                          save_manifest, summary)

REPO = Path(__file__).resolve().parent.parent
TOP_ROOT = REPO.parent  # true repo root — persona configs' paths are relative to this
PERSONAS = REPO / "examples" / "intake-personas"


def _resolve_relative(value):
    """Persona configs use paths relative to the true repo root (same convention as
    ./chain: CWD stays at the repo root, ENGINE is exposed via PYTHONPATH, not cd).
    Make them absolute against TOP_ROOT right after loading, so classify()/
    walk_source() work regardless of the test runner's own CWD."""
    if isinstance(value, str) and value and not value.startswith("~") and not Path(value).is_absolute():
        return str((TOP_ROOT / value).resolve())
    return value


def persona_config(name, home):
    cfg = load_config(local_path=PERSONAS / f"{name}.config.yaml", check_paths=False)
    for key in ("voice_spec", "positioning_pillars", "lint_overrides", "feedback_ledger"):
        if key in cfg:
            cfg[key] = _resolve_relative(cfg[key])
    for source in cfg.get("sources", []):
        source["path"] = _resolve_relative(source["path"])
    cfg["chain_home"] = str(home)
    cfg["library_dir"] = str(Path(home) / "library")
    cfg["workspace_dir"] = str(Path(home) / "workspace")
    return cfg


class RegistryTests(unittest.TestCase):
    def test_keys_unique_and_tiers_valid(self):
        keys = [a.key for a in REGISTRY]
        self.assertEqual(len(keys), len(set(keys)))
        for a in REGISTRY:
            self.assertIn(a.tier, ("required", "recommended", "optional"))

    def test_required_set_is_the_writing_quality_core(self):
        required = {a.key for a in REGISTRY if a.tier == "required"}
        self.assertEqual(required, {"source_map", "corpus", "voice_spec", "positioning"})

    def test_every_declared_template_ships_in_repo(self):
        for a in REGISTRY:
            if a.template:
                self.assertTrue((REPO / a.template).exists(), a.template)


class ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _cfg(self, **over):
        cfg = {"chain_home": str(self.home), "sources": [],
               "voice_spec": "", "positioning_pillars": ""}
        cfg.update(over)
        return cfg

    def test_absent_file_is_missing(self):
        cls, _ = classify(self._cfg())
        self.assertEqual(cls["voice_spec"]["status"], "missing")

    def test_thin_file_is_partial(self):
        p = self.home / "voice-spec.md"
        p.write_text("# Voice\n\nBe direct.\n", encoding="utf-8")
        cls, _ = classify(self._cfg(voice_spec=str(p)))
        self.assertEqual(cls["voice_spec"]["status"], "partial")

    def test_untouched_template_copy_is_partial(self):
        p = self.home / "voice-spec.md"
        p.write_text((REPO / "canon" / "voice-spec.template.md").read_text(encoding="utf-8"),
                     encoding="utf-8")
        cls, _ = classify(self._cfg(voice_spec=str(p)))
        self.assertEqual(cls["voice_spec"]["status"], "partial")
        self.assertIn("template", cls["voice_spec"]["detail"])

    def test_substantive_file_exists(self):
        p = self.home / "voice-spec.md"
        p.write_text("# Voice\n\n" + "Real sentence with several words here. " * 30,
                     encoding="utf-8")
        cls, _ = classify(self._cfg(voice_spec=str(p)))
        self.assertEqual(cls["voice_spec"]["status"], "exists")

    def test_pillars_need_a_parseable_table(self):
        p = self.home / "pillars.md"
        p.write_text("# Pillars\n\nSome prose about positioning goals but no table. "
                     * 5, encoding="utf-8")
        cls, _ = classify(self._cfg(positioning_pillars=str(p)))
        self.assertEqual(cls["positioning"]["status"], "partial")
        p.write_text("| id | Label |\n|---|---|\n| `builder` | Builder |\n",
                     encoding="utf-8")
        cls, _ = classify(self._cfg(positioning_pillars=str(p)))
        self.assertEqual(cls["positioning"]["status"], "exists")

    def test_manifest_recorded_path_wins_over_default(self):
        real = self.home / "kept-elsewhere.md"
        real.write_text("words " * 200, encoding="utf-8")
        manifest = {"assets": {"themes": {"path": str(real)}}}
        cls, _ = classify(self._cfg(), manifest)
        self.assertEqual(cls["themes"]["status"], "exists")
        self.assertEqual(cls["themes"]["path"], str(real))


class PersonaTests(unittest.TestCase):
    """The three committed synthetic personas classify to their intended levels."""

    def _run(self, name):
        self.tmp = tempfile.TemporaryDirectory()
        cfg = persona_config(name, self.tmp.name)
        cls, stats = classify(cfg)
        return cfg, cls, stats

    def test_p1_organized_is_level_1_with_nothing_to_recreate(self):
        _, cls, stats = self._run("p1-organized")
        self.assertEqual(maturity_level(cls, stats), 1)
        for key in ("source_map", "corpus", "voice_spec", "positioning"):
            self.assertEqual(cls[key]["status"], "exists", key)
        plan = build_plan(cls)
        self.assertEqual([s for s in plan if s["blocking"]], [])
        self.assertTrue(all(s["status"] == "missing" and s["tier"] != "required"
                            for s in plan))

    def test_p2_studio_is_level_2_distill_case(self):
        _, cls, stats = self._run("p2-studio")
        self.assertEqual(maturity_level(cls, stats), 2)
        self.assertEqual(cls["source_map"]["status"], "exists")
        self.assertEqual(cls["corpus"]["status"], "partial")
        self.assertEqual(cls["voice_spec"]["status"], "missing")
        blockers = [s["asset"] for s in build_plan(cls) if s["blocking"]]
        self.assertIn("voice_spec", blockers)
        self.assertIn("positioning", blockers)
        # partial = usable-but-thin: strengthens, never blocks
        self.assertNotIn("corpus", blockers)

    def test_p3_newcomer_is_level_3_create_case_not_a_rejection(self):
        _, cls, stats = self._run("p3-newcomer")
        self.assertEqual(maturity_level(cls, stats), 3)
        plan = build_plan(cls)
        corpus_step = next(s for s in plan if s["asset"] == "corpus")
        self.assertEqual(corpus_step["action"], "locate-or-create")
        self.assertIn("exercise", corpus_step["step"].lower())
        # every blocker carries a purpose and a smallest useful step — the plan
        # teaches, it doesn't just report absences
        for s in plan:
            self.assertTrue(s["why"] and s["step"], s["asset"])


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = persona_config("p2-studio", self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_roundtrip_preserves_human_fields_and_recomputes_status(self):
        m1 = build_manifest(self.cfg, today="2026-01-01")
        m1["assets"]["voice_spec"]["provenance"] = "created"
        m1["assets"]["story_bank"]["skipped"] = True
        save_manifest(self.cfg, m1)
        m2 = build_manifest(self.cfg, today="2026-01-02")
        self.assertEqual(m2["created"], "2026-01-01")
        self.assertEqual(m2["updated"], "2026-01-02")
        self.assertEqual(m2["assets"]["voice_spec"]["provenance"], "created")
        self.assertTrue(m2["assets"]["story_bank"]["skipped"])
        self.assertEqual(m2["assets"]["voice_spec"]["status"], "missing")

    def test_manifest_contains_no_source_content(self):
        m = build_manifest(self.cfg)
        blob = json.dumps(m)
        faq = (REPO / "examples" / "demo-sources-studio" / "faqs" /
               "client-questions.md").read_text(encoding="utf-8")
        probe = max(faq.splitlines(), key=len).strip()
        self.assertNotIn(probe[:40], blob)

    def test_blockers_and_skip_flow_in_summary(self):
        m = build_manifest(self.cfg)
        cls, _ = classify(self.cfg, m)
        text = summary(m, build_plan(cls, m))
        self.assertIn("Blocks writing quality", text)
        self.assertIn("maturity level 2", text)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        # a persona config copy whose chain_home points at the temp dir
        raw = (PERSONAS / "p1-organized.config.yaml").read_text(encoding="utf-8")
        raw = raw.replace("./.chain/intake-p1", str(self.home))
        raw = raw.replace("./ENGINE__PUBLIC_GIT_TRACKED/examples/", str(REPO / "examples") + "/")
        self.cfg_path = Path(self.tmp.name) / "cfg.yaml"
        self.cfg_path.write_text(raw, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_cli_inspects_marks_and_persists(self):
        rc = main([str(self.cfg_path), "--mark", "voice_spec=user-provided",
                   "--skip", "story_bank"])
        self.assertEqual(rc, 0)
        cfg = load_config(local_path=self.cfg_path, check_paths=False)
        m = load_manifest(cfg)
        self.assertEqual(m["maturity_level"], 1)
        self.assertEqual(m["assets"]["voice_spec"]["provenance"], "user-provided")
        self.assertTrue(m["assets"]["story_bank"]["skipped"])
        self.assertTrue(manifest_path(cfg).exists())

    def test_cli_note_persists(self):
        main([str(self.cfg_path), "--note", "corpus=grow toward 8 pieces"])
        cfg = load_config(local_path=self.cfg_path, check_paths=False)
        m = load_manifest(cfg)
        self.assertEqual(m["assets"]["corpus"]["notes"], "grow toward 8 pieces")

    def test_cli_rejects_bad_marks(self):
        with self.assertRaises(SystemExit):
            main([str(self.cfg_path), "--mark", "nonsense=created"])
        with self.assertRaises(SystemExit):
            main([str(self.cfg_path), "--skip", "voice_spec"])  # required


if __name__ == "__main__":
    unittest.main()
