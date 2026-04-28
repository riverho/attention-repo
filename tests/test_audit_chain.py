#!/usr/bin/env python3
"""Finalize lifecycle regression tests."""

import argparse
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from scripts.jit_context import (
    cmd_finalize_change,
    cmd_map_freshness_check,
    declaration_path,
    default_map_template,
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
def repo_with_intent():
    tmp = tempfile.TemporaryDirectory()
    repo = Path(tmp.name)
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
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
    subprocess.run(["git", "add", "."], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    try:
        yield repo
    finally:
        tmp.cleanup()


def finalize(repo):
    cmd_finalize_change(
        argparse.Namespace(
            repo=str(repo),
            tests_command="python3 -m unittest",
            tests_result="pass",
            notes="test finalize",
        )
    )


class TestFinalizeWithoutFreshness(unittest.TestCase):
    def test_finalize_blocked_without_freshness(self):
        with repo_with_intent() as repo:
            with self.assertRaises(SystemExit):
                finalize(repo)


class TestFullLifecycle(unittest.TestCase):
    def test_complete_lifecycle(self):
        with repo_with_intent() as repo:
            cmd_map_freshness_check(argparse.Namespace(repo=str(repo), no_change_justification=None))
            finalize(repo)
            report = (repo / ".attention" / "ATTENTION_FINALIZE.md").read_text(encoding="utf-8")
            self.assertIn("Tests Result: pass", report)
            self.assertIn("E-APP-01", report)
            self.assertIn("Map Freshness", report)


if __name__ == "__main__":
    unittest.main()
