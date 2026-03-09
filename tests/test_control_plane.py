#!/usr/bin/env python3
"""Tests for the central attention-layer control plane."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.resolve import detect_project_candidates, get_config_path, get_index_path, load_index, load_config


class ControlPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.workspace = self.root / "workspace"
        self.projects_root = self.workspace / "projects"
        self.skills_root = self.workspace / "skills"
        self.projects_root.mkdir(parents=True)
        self.skills_root.mkdir(parents=True)

        (self.projects_root / "alpha").mkdir()
        (self.projects_root / "alpha" / ".git").mkdir()
        (self.projects_root / "beta").mkdir()
        (self.projects_root / "beta" / "package.json").write_text("{}", encoding="utf-8")
        (self.skills_root / "attention-layer").mkdir()
        (self.skills_root / "attention-layer" / "README.md").write_text("skill", encoding="utf-8")

        self.openclaw_config_path = self.root / "openclaw.json"
        self.openclaw_config_path.write_text(
            json.dumps(
                {
                    "agents": {
                        "defaults": {
                            "workspace": str(self.workspace),
                            "model": {
                                "primary": "minimax-portal/MiniMax-M2.5",
                                "fallbacks": ["kimi-coding/k2p5"],
                            },
                            "models": {"minimax-portal/MiniMax-M2.5": {"alias": "minimax"}},
                        }
                    },
                    "models": {
                        "providers": {
                            "minimax-portal": {"models": [{"id": "MiniMax-M2.5"}]},
                            "kimi-coding": {"models": [{"id": "k2p5"}]},
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        self.state_root = self.root / "state"
        self._env = mock.patch.dict(
            os.environ,
            {
                "ATTENTION_LAYER_STATE_ROOT": str(self.state_root),
                "OPENCLAW_CONFIG_PATH": str(self.openclaw_config_path),
            },
        )
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()
        self._tmpdir.cleanup()

    def test_detect_project_candidates_projects_only_by_default(self) -> None:
        candidates = detect_project_candidates()
        names = [candidate["name"] for candidate in candidates]
        self.assertEqual(names, ["alpha", "beta"])

        expanded = detect_project_candidates(include_skills=True)
        expanded_names = [candidate["name"] for candidate in expanded]
        self.assertEqual(expanded_names, ["alpha", "beta", "attention-layer"])

    def test_init_workspace_creates_templates_and_central_index(self) -> None:
        env = dict(os.environ)
        env["ATTENTION_LAYER_STATE_ROOT"] = str(self.state_root)
        env["OPENCLAW_CONFIG_PATH"] = str(self.openclaw_config_path)
        subprocess.run(
            ["python3", "scripts/jit-context.py", "init"],
            cwd=Path(__file__).resolve().parent.parent,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        config = load_config()
        self.assertEqual(sorted(config["projects"].keys()), ["alpha", "beta"])
        self.assertTrue(get_config_path().exists())
        self.assertTrue(get_index_path().exists())

        for project_name in ("alpha", "beta"):
            repo = self.projects_root / project_name
            self.assertTrue((repo / "!MAP.md").exists())
            self.assertTrue((repo / "CURRENT_TASK.md").exists())

        index = load_index()
        self.assertEqual(sorted(index["projects"].keys()), ["alpha", "beta"])


if __name__ == "__main__":
    unittest.main()
