#!/usr/bin/env python3
"""Gate effectiveness regression tests."""

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from scripts.jit_context import (
    default_map_template,
    ensure_templates,
    extract_entity_registry,
    validate_declaration,
    write_entity_registry,
)


@contextmanager
def make_repo(entities):
    tmp = tempfile.TemporaryDirectory()
    repo = Path(tmp.name)
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / ".github" / "workflows" / "api.yml").write_text("name: api\n", encoding="utf-8")
    (repo / ".github" / "workflows" / "worker.yml").write_text("name: worker\n", encoding="utf-8")
    for entity in entities:
        path = repo / entity["file_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# entity\n", encoding="utf-8")
    (repo / "!MAP.md").write_text(default_map_template(), encoding="utf-8")
    write_entity_registry(repo / "!MAP.md", {"entities": entities})
    try:
        yield repo
    finally:
        tmp.cleanup()


ENTITY_A = {
    "id": "E-API-01",
    "type": "Script",
    "file_path": "src/api.py",
    "ci_cd": ".github/workflows/api.yml",
    "endpoint": "CLI: api",
    "description": "API entity",
}
ENTITY_B = {
    "id": "E-JOBS-01",
    "type": "Script",
    "file_path": "src/jobs.py",
    "ci_cd": ".github/workflows/api.yml",
    "endpoint": "CLI: jobs",
    "description": "Jobs entity",
}
ENTITY_C = {
    "id": "E-WORKER-01",
    "type": "Script",
    "file_path": "src/worker.py",
    "ci_cd": ".github/workflows/worker.yml",
    "endpoint": "CLI: worker",
    "description": "Worker entity",
}


class TestColdStartInit(unittest.TestCase):
    def test_init_creates_template_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            ensure_templates(repo)
            self.assertTrue((repo / "!MAP.md").exists())
            self.assertTrue((repo / "CURRENT_TASK.md").exists())
            self.assertEqual(extract_entity_registry((repo / "!MAP.md").read_text())["entities"], [])


class TestEntityRegistryPopulation(unittest.TestCase):
    def test_parse_entity_registry(self):
        with make_repo([ENTITY_A, ENTITY_B, ENTITY_C]) as repo:
            registry = extract_entity_registry((repo / "!MAP.md").read_text())
            self.assertEqual([e["id"] for e in registry["entities"]], ["E-API-01", "E-JOBS-01", "E-WORKER-01"])


class TestValidSingleEntity(unittest.TestCase):
    def test_single_entity_declaration(self):
        with make_repo([ENTITY_A]) as repo:
            validate_declaration(repo, ["E-API-01"], ".github/workflows/api.yml", "Change API behavior with scoped validation", False, "code")


class TestValidMultiEntitySamePipeline(unittest.TestCase):
    def test_multi_entity_same_pipeline(self):
        with make_repo([ENTITY_A, ENTITY_B]) as repo:
            validate_declaration(repo, ["E-API-01", "E-JOBS-01"], ".github/workflows/api.yml", "Change both API entities through same pipeline", False, "code")


class TestRejectNonExistentEntity(unittest.TestCase):
    def test_unknown_entity_rejected(self):
        with make_repo([ENTITY_A]) as repo:
            with self.assertRaisesRegex(ValueError, "Unknown entity"):
                validate_declaration(repo, ["E-PAYMENTS-99"], ".github/workflows/api.yml", "Change unknown payment entity safely through gate", False, "code")


class TestRejectPipelineMismatch(unittest.TestCase):
    def test_pipeline_mismatch(self):
        with make_repo([ENTITY_A]) as repo:
            with self.assertRaisesRegex(ValueError, "deployment_pipeline must match"):
                validate_declaration(repo, ["E-API-01"], ".github/workflows/worker.yml", "Change API but wrong deployment pipeline", False, "code")


class TestRejectNonExistentPipeline(unittest.TestCase):
    def test_nonexistent_pipeline(self):
        with make_repo([ENTITY_A]) as repo:
            with self.assertRaisesRegex(ValueError, "deployment_pipeline does not exist"):
                validate_declaration(repo, ["E-API-01"], ".github/workflows/missing.yml", "Change API with missing pipeline file", False, "code")


class TestRejectShortSummary(unittest.TestCase):
    def test_short_summary_rejected(self):
        with make_repo([ENTITY_A]) as repo:
            with self.assertRaisesRegex(ValueError, "at least 6 words"):
                validate_declaration(repo, ["E-API-01"], ".github/workflows/api.yml", "too short", False, "code")


class TestRejectCrossPipelineConflict(unittest.TestCase):
    def test_cross_pipeline_rejected(self):
        with make_repo([ENTITY_A, ENTITY_C]) as repo:
            with self.assertRaisesRegex(ValueError, "deployment_pipeline must match"):
                validate_declaration(repo, ["E-API-01", "E-WORKER-01"], ".github/workflows/api.yml", "Change conflicting entities across deployment pipelines", False, "code")


class TestEntityNoPipeline(unittest.TestCase):
    def test_null_ci_cd_handling(self):
        entity = {**ENTITY_A, "ci_cd": None}
        with make_repo([entity]) as repo:
            validate_declaration(repo, ["E-API-01"], ".github/workflows/api.yml", "Change entity without explicit pipeline mapping", False, "code")


class TestEntitySchema(unittest.TestCase):
    def test_duplicate_entity_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate entity id"):
            with make_repo([ENTITY_A, {**ENTITY_B, "id": "E-API-01"}]) as repo:
                extract_entity_registry((repo / "!MAP.md").read_text())


if __name__ == "__main__":
    unittest.main()
