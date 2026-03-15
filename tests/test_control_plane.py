#!/usr/bin/env python3
"""Tests for the central attention-repo control plane."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import scripts.resolve as resolve
from scripts.attention_state import get_state as get_attention_state
from scripts.resolve import (
    build_default_config,
    detect_project_candidates,
    get_config_path,
    get_index_path,
    get_project_display_name,
    load_index,
    load_config,
    resolve_project_key,
    save_index,
    save_config,
    summarize_current_task,
)
from scripts.version_info import VERSION_FILE, get_version


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
        (self.skills_root / "attention-repo").mkdir()
        (self.skills_root / "attention-repo" / "README.md").write_text("skill", encoding="utf-8")

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
                "ATTENTION_REPO_STATE_ROOT": str(self.state_root),
                "OPENCLAW_CONFIG_PATH": str(self.openclaw_config_path),
            },
        )
        self._env.start()
        save_index(
            {
                "version": "1",
                "created_at": "2026-03-15T07:00:00+00:00",
                "last_updated": "2026-03-15T07:00:00+00:00",
                "projects": {},
                "skill_runtime": {"compiled_version": get_version()},
            },
            get_index_path(),
        )

    def tearDown(self) -> None:
        self._env.stop()
        self._tmpdir.cleanup()

    def test_detect_project_candidates_projects_only_by_default(self) -> None:
        config = build_default_config()
        candidates = detect_project_candidates(config)
        names = [candidate["name"] for candidate in candidates]
        self.assertEqual(names, ["alpha", "beta"])

        expanded = detect_project_candidates(config, include_skills=True)
        expanded_names = [candidate["name"] for candidate in expanded]
        self.assertEqual(expanded_names, ["alpha", "beta", "attention-repo"])

    def test_init_workspace_creates_templates_and_central_index(self) -> None:
        env = dict(os.environ)
        env["ATTENTION_REPO_STATE_ROOT"] = str(self.state_root)
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

    def test_init_with_include_skills_persists_skill_scope(self) -> None:
        env = dict(os.environ)
        env["ATTENTION_REPO_STATE_ROOT"] = str(self.state_root)
        env["OPENCLAW_CONFIG_PATH"] = str(self.openclaw_config_path)
        subprocess.run(
            ["python3", "scripts/jit-context.py", "init", "--include-skills"],
            cwd=Path(__file__).resolve().parent.parent,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        config = load_config()
        self.assertEqual(config["projects"]["attention-repo"]["scope"], "skills")
        self.assertTrue(config["projects"]["attention-repo"]["menu_visible"])

        index = load_index()
        self.assertEqual(index["projects"]["attention-repo"]["scope"], "skills")

    def test_load_config_migrates_legacy_projects_into_empty_central_config(self) -> None:
        legacy_path = self.root / "legacy-attention-config.json"
        legacy_path.write_text(
            json.dumps(
                {
                    "$schema": "attention_repo-config-v1",
                    "project_registry": {
                        "attention_repo": {
                            "canonical_path": str(self.skills_root / "attention-repo"),
                            "source_strategy": "local_only",
                        },
                        "beta": {
                            "canonical_path": str(self.projects_root / "beta"),
                            "source_strategy": "local_only",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        save_config(build_default_config(), get_config_path())
        with mock.patch.object(resolve, "LEGACY_CONFIG_PATH", legacy_path):
            config = load_config()

        self.assertEqual(sorted(config["projects"].keys()), ["attention_repo", "beta"])
        persisted = json.loads(get_config_path().read_text(encoding="utf-8"))
        self.assertEqual(sorted(persisted["projects"].keys()), ["attention_repo", "beta"])

    def test_load_config_prefers_non_empty_central_config_over_legacy(self) -> None:
        legacy_path = self.root / "legacy-attention-config.json"
        legacy_path.write_text(
            json.dumps(
                {
                    "$schema": "attention_repo-config-v1",
                    "project_registry": {
                        "legacy-only": {
                            "canonical_path": str(self.projects_root / "alpha"),
                            "source_strategy": "local_only",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        config = build_default_config()
        config["projects"] = {
            "central-only": {
                "canonical_path": str(self.projects_root / "beta"),
                "source_strategy": "local_only",
                "managed": True,
                "source": "projects",
            }
        }
        save_config(config, get_config_path())

        with mock.patch.object(resolve, "LEGACY_CONFIG_PATH", legacy_path):
            loaded = load_config()

        self.assertEqual(sorted(loaded["projects"].keys()), ["central-only"])

    def test_resolve_project_key_prefers_exact_alias_before_fuzzy_match(self) -> None:
        config = build_default_config()
        config["projects"] = {
            "summon-A2A-academy": {
                "canonical_path": str(self.projects_root / "alpha"),
                "source_strategy": "local_only",
                "aliases": ["academy"],
            },
            "summon": {
                "canonical_path": str(self.projects_root / "beta"),
                "source_strategy": "local_only",
            },
        }
        self.assertEqual(resolve_project_key("academy", config), "summon-A2A-academy")
        self.assertEqual(resolve_project_key("summon", config), "summon")

    def test_display_name_defaults_to_repo_folder_name(self) -> None:
        config = build_default_config()
        config["projects"] = {
            "attention_repo": {
                "canonical_path": str(self.skills_root / "attention-repo"),
                "source_strategy": "local_only",
            }
        }
        self.assertEqual(get_project_display_name("attention_repo", config), "attention-repo")

    def test_canonical_version_file_is_the_single_runtime_source(self) -> None:
        payload = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
        self.assertEqual(get_version(), payload["version"])

    def test_attention_help_reads_canonical_version(self) -> None:
        env = dict(os.environ)
        env["ATTENTION_REPO_STATE_ROOT"] = str(self.state_root)
        env["OPENCLAW_CONFIG_PATH"] = str(self.openclaw_config_path)

        result = subprocess.run(
            ["scripts/attention", "--help"],
            cwd=Path(__file__).resolve().parent.parent,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn(f"attention - attention repo CLI (v{get_version()})", result.stdout)

    def test_update_gate_requires_bootstrap_when_compiled_version_is_stale(self) -> None:
        index = load_index()
        index["skill_runtime"] = {"compiled_version": "0.3.0"}
        save_index(index, get_index_path())

        gate = resolve.get_update_gate_status(get_version(), index=load_index())
        self.assertTrue(gate["required"])
        self.assertEqual(gate["compiled_version"], "0.3.0")

    def test_bootstrap_update_compiles_current_version_into_index(self) -> None:
        env = dict(os.environ)
        env["ATTENTION_REPO_STATE_ROOT"] = str(self.state_root)
        env["OPENCLAW_CONFIG_PATH"] = str(self.openclaw_config_path)

        result = subprocess.run(
            ["python3", "scripts/jit-context.py", "bootstrap-update"],
            cwd=Path(__file__).resolve().parent.parent,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        index = load_index()
        self.assertEqual(index["skill_runtime"]["compiled_version"], get_version())
        self.assertIn("Gate cleared: yes", result.stdout)

    def test_start_is_blocked_until_bootstrap_after_version_mismatch(self) -> None:
        index = load_index()
        index["skill_runtime"] = {"compiled_version": "0.3.0"}
        save_index(index, get_index_path())

        env = dict(os.environ)
        env["ATTENTION_REPO_STATE_ROOT"] = str(self.state_root)
        env["OPENCLAW_CONFIG_PATH"] = str(self.openclaw_config_path)

        result = subprocess.run(
            ["scripts/attention", "start", str(self.projects_root / "alpha")],
            cwd=Path(__file__).resolve().parent.parent,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bootstrap-update", result.stdout)

    def test_release_attention_marks_repo_as_released(self) -> None:
        repo = self.projects_root / "alpha"
        (repo / "CURRENT_TASK.md").write_text(
            "# CURRENT_TASK.md\n\n## Status\nIn progress: ship alias routing.\n",
            encoding="utf-8",
        )

        env = dict(os.environ)
        env["ATTENTION_REPO_STATE_ROOT"] = str(self.state_root)
        env["OPENCLAW_CONFIG_PATH"] = str(self.openclaw_config_path)
        subprocess.run(
            ["python3", "scripts/jit-context.py", "release-attention", str(repo), "--note", "Wrapped cleanly."],
            cwd=Path(__file__).resolve().parent.parent,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        text = (repo / "CURRENT_TASK.md").read_text(encoding="utf-8")
        self.assertIn("## Attention State", text)
        self.assertIn("State: Released", text)
        status, summary = summarize_current_task(repo)
        self.assertEqual(status, "released")
        self.assertEqual(summary, "In progress: ship alias routing.")

    def test_start_alias_without_task_shows_canonical_focus(self) -> None:
        config = build_default_config()
        config["projects"] = {
            "attention_repo": {
                "canonical_path": str(self.projects_root / "alpha"),
                "source_strategy": "local_only",
                "aliases": ["attnrepo"],
            }
        }
        save_config(config, get_config_path())
        (self.projects_root / "alpha" / "CURRENT_TASK.md").write_text(
            "# CURRENT_TASK.md\n\n## Status\nIn progress: verify alias focus path.\n",
            encoding="utf-8",
        )

        env = dict(os.environ)
        env["ATTENTION_REPO_STATE_ROOT"] = str(self.state_root)
        env["OPENCLAW_CONFIG_PATH"] = str(self.openclaw_config_path)
        result = subprocess.run(
            ["scripts/attention", "start", "attnrepo"],
            cwd=Path(__file__).resolve().parent.parent,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn(str(self.projects_root / "alpha"), result.stdout)
        self.assertIn("verify alias focus path", result.stdout)
        self.assertIn("attention start attnrepo", result.stdout)
        state = get_attention_state()
        self.assertEqual(state["active"], "alpha")
        self.assertEqual(Path(state["active_path"]).resolve(), (self.projects_root / "alpha").resolve())

    def test_release_attention_cli_updates_global_state_note(self) -> None:
        repo = self.projects_root / "alpha"
        env = dict(os.environ)
        env["ATTENTION_REPO_STATE_ROOT"] = str(self.state_root)
        env["OPENCLAW_CONFIG_PATH"] = str(self.openclaw_config_path)

        subprocess.run(
            ["scripts/attention", "start", str(repo)],
            cwd=Path(__file__).resolve().parent.parent,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["scripts/attention", "release-attention", str(repo), "--note", "Wrapped cleanly."],
            cwd=Path(__file__).resolve().parent.parent,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        state = get_attention_state()
        self.assertIsNone(state["active"])
        self.assertEqual(state["release_note"], "Wrapped cleanly.")

    def test_refresh_project_record_ignores_map_sync_newer_than_assemble(self) -> None:
        repo = self.projects_root / "alpha"
        map_path = repo / "!MAP.md"
        map_path.write_text("# !MAP.md\n\n## Entity Registry\n", encoding="utf-8")

        record = resolve.refresh_project_record(
            "alpha",
            repo,
            {
                "last_assemble": "2026-03-13T11:28:31+00:00",
                "last_freshness": "2026-03-15T06:46:28+00:00",
                "last_sync_state": "2099-03-15T06:46:29+00:00",
            },
        )

        self.assertFalse(record["stale"])
        self.assertEqual(record["warnings"], [])

    def test_summarize_current_task_prefers_release_note_when_status_empty(self) -> None:
        repo = self.projects_root / "alpha"
        (repo / "CURRENT_TASK.md").write_text(
            "\n".join(
                [
                    "# CURRENT_TASK.md",
                    "",
                    "## Status",
                    "",
                    "## Attention State",
                    "- State: Released",
                    "- Released At: 2026-03-15T06:46:29+00:00",
                    "- Note: Released via service_router wrap flow",
                    "",
                    "## Older Context",
                    "- Legacy summary that should not win.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        status, summary = summarize_current_task(repo)
        self.assertEqual(status, "released")
        self.assertEqual(summary, "Released via service_router wrap flow")

    def test_reinit_rebuilds_corrupt_files_and_salvages_task_excerpt(self) -> None:
        repo = self.projects_root / "alpha"
        (repo / "!MAP.md").write_text("broken map", encoding="utf-8")
        (repo / "CURRENT_TASK.md").write_text("legacy note: repo memory needs recovery", encoding="utf-8")

        env = dict(os.environ)
        env["ATTENTION_REPO_STATE_ROOT"] = str(self.state_root)
        env["OPENCLAW_CONFIG_PATH"] = str(self.openclaw_config_path)
        subprocess.run(
            ["python3", "scripts/jit-context.py", "reinit", str(repo)],
            cwd=Path(__file__).resolve().parent.parent,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        map_text = (repo / "!MAP.md").read_text(encoding="utf-8")
        task_text = (repo / "CURRENT_TASK.md").read_text(encoding="utf-8")
        self.assertIn("# !MAP.md", map_text)
        self.assertIn("Recovered task memory requires review", task_text)
        self.assertIn("legacy note: repo memory needs recovery", task_text)
        recovery_root = repo / ".attention" / "recovery"
        self.assertTrue(recovery_root.exists())


if __name__ == "__main__":
    unittest.main()
