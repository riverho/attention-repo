#!/usr/bin/env python3
"""Map freshness and drift regression tests."""

import argparse
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from scripts.jit_context import (
    cmd_map_freshness_check,
    declaration_path,
    default_map_template,
    extract_entity_registry,
    write_entity_registry,
    write_text,
)


ENTITY = {
    "id": "E-APP-01",
    "type": "Script",
    "file_path": "src/app.py",
    "ci_cd": ".github/workflows/ci.yml",
    "endpoint": "CLI: app",
    "description": "Application entity",
}


@contextmanager
def repo_with_declaration():
    tmp = tempfile.TemporaryDirectory()
    repo = Path(tmp.name)
    (repo / "src").mkdir()
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".attention").mkdir()
    (repo / "src" / "app.py").write_text("# app\n", encoding="utf-8")
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (repo / "!MAP.md").write_text(default_map_template(), encoding="utf-8")
    write_entity_registry(repo / "!MAP.md", {"entities": [ENTITY]})
    write_text(
        declaration_path(repo),
        '{"affected_entities":["E-APP-01"],"deployment_pipeline":".github/workflows/ci.yml","first_principle_summary":"Change app with focused boundary validation","requires_new_entity":false}\n',
    )
    try:
        yield repo
    finally:
        tmp.cleanup()


def run_freshness(repo):
    cmd_map_freshness_check(argparse.Namespace(repo=str(repo), no_change_justification=None))


class TestFreshnessCleanState(unittest.TestCase):
    def test_clean_state_passes(self):
        with repo_with_declaration() as repo:
            run_freshness(repo)
            self.assertIn('"status": "PASS"', (repo / ".attention" / "map_freshness.json").read_text())


class TestFreshnessDeletedFile(unittest.TestCase):
    def test_deleted_file_blocked(self):
        with repo_with_declaration() as repo:
            (repo / "src" / "app.py").unlink()
            with self.assertRaises(SystemExit):
                run_freshness(repo)
            self.assertIn("file_path", (repo / ".attention" / "map_freshness.json").read_text())


class TestFreshnessDeletedPipeline(unittest.TestCase):
    def test_deleted_pipeline_blocked(self):
        with repo_with_declaration() as repo:
            (repo / ".github" / "workflows" / "ci.yml").unlink()
            with self.assertRaises(SystemExit):
                run_freshness(repo)
            self.assertIn("ci_cd", (repo / ".attention" / "map_freshness.json").read_text())


class TestContentDriftHash(unittest.TestCase):
    def test_content_changed_detected_by_freshness_timestamp(self):
        with repo_with_declaration() as repo:
            run_freshness(repo)
            before = (repo / ".attention" / "map_freshness.json").read_text()
            (repo / "src" / "app.py").write_text("# changed\n", encoding="utf-8")
            run_freshness(repo)
            after = (repo / ".attention" / "map_freshness.json").read_text()
            self.assertIn('"status": "PASS"', after)
            self.assertNotEqual(before, after)


class TestGitConflictDetection(unittest.TestCase):
    def test_conflict_markers_detected(self):
        with repo_with_declaration() as repo:
            text = (repo / "!MAP.md").read_text()
            with self.assertRaisesRegex(ValueError, "conflict markers"):
                extract_entity_registry("<<<<<<< HEAD\n" + text + "\n>>>>>>> branch\n")


class TestBranchSpecificPipelines(unittest.TestCase):
    def test_branch_aware_pipeline_defaults_to_registered_pipeline(self):
        with repo_with_declaration() as repo:
            run_freshness(repo)
            record = (repo / ".attention" / "map_freshness.json").read_text()
            self.assertIn(".github/workflows/ci.yml", record)


if __name__ == "__main__":
    unittest.main()
