#!/usr/bin/env python3
"""Regression tests for Telegram/OpenClaw routing flows."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.service_router import RouteRequest, _user_sessions, route
from scripts.version_info import get_version
from scripts.openclaw_router_bridge import _rewrite_buttons


class ServiceRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        _user_sessions.clear()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.state_root = os.path.join(self._tmpdir.name, "state")
        self.openclaw_config_path = os.path.join(self._tmpdir.name, "openclaw.json")
        with open(self.openclaw_config_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "agents": {
                        "defaults": {
                            "workspace": os.path.join(self._tmpdir.name, "workspace"),
                            "model": {"primary": "minimax-portal/MiniMax-M2.5", "fallbacks": []},
                            "models": {},
                        }
                    },
                    "models": {"providers": {}},
                },
                handle,
            )
        self.project_root = Path(self._tmpdir.name) / "workspace" / "projects" / "attention_repo"
        self.project_root.mkdir(parents=True)
        (self.project_root / "!MAP.md").write_text("# !MAP.md\n", encoding="utf-8")
        (self.project_root / "CURRENT_TASK.md").write_text(
            "# CURRENT_TASK.md\n\nIn progress: refine repo focus flow.\n",
            encoding="utf-8",
        )
        state_root_path = Path(self.state_root)
        state_root_path.mkdir(parents=True)
        with open(state_root_path / "config.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "$schema": "attention-repo-config-v2",
                    "projects": {
                        "attention_repo": {
                            "canonical_path": str(self.project_root),
                            "source_strategy": "local_only",
                            "managed": True,
                            "source": "test",
                        }
                    },
                },
                handle,
            )
        with open(state_root_path / "index.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "version": "1",
                    "created_at": "2026-03-15T07:00:00+00:00",
                    "last_updated": "2026-03-15T07:00:00+00:00",
                    "projects": {},
                    "skill_runtime": {"compiled_version": get_version()},
                },
                handle,
            )
        self._env = patch.dict(
            os.environ,
            {
                "ATTENTION_REPO_STATE_ROOT": self.state_root,
                "OPENCLAW_CONFIG_PATH": self.openclaw_config_path,
            },
        )
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()
        self._tmpdir.cleanup()

    def test_start_callback_requires_confirmation(self) -> None:
        response = route(RouteRequest(text="attn:start:attention_repo", user_id="test-start", platform="telegram"))
        self.assertIn("confirm-start@attention_repo", response.text)
        self.assertIn("Confirm focus on", response.text)
        self.assertTrue(response.suggest_menu)

    def test_confirm_start_callback_shows_latest_task_summary(self) -> None:
        user_id = "test-confirm-start"
        route(RouteRequest(text="attn:start:attention_repo", user_id=user_id, platform="telegram"))
        response = route(RouteRequest(text="attn:confirm-start:attention_repo", user_id=user_id, platform="telegram"))
        self.assertIn("focus@attention_repo", response.text)
        self.assertIn("Last recorded focus", response.text)
        self.assertIn("refine repo focus flow", response.text)

    @patch("scripts.service_router.run_cli")
    def test_follow_up_message_updates_task_after_start(self, run_cli) -> None:
        run_cli.side_effect = [
            ("task-saved", "", 0),
            ("assemble-complete", "", 0),
        ]
        user_id = "test-follow-up"
        first = route(RouteRequest(text="attn:start:attention_repo", user_id=user_id, platform="telegram"))
        self.assertIn("Confirm focus on", first.text)

        second = route(RouteRequest(text="attn:confirm-start:attention_repo", user_id=user_id, platform="telegram"))
        self.assertIn("Reply with what you want to work on next.", second.text)

        third = route(
            RouteRequest(
                text="Fix auth callback redirect and clean stale buttons",
                user_id=user_id,
                platform="telegram",
            )
        )
        self.assertIn("Saved your focus and refreshed project context.", third.text)
        self.assertEqual(third.structured_data["command"], "start")
        self.assertEqual(run_cli.call_args_list[0].args[0], "update-task")
        self.assertEqual(run_cli.call_args_list[1].args[0], "assemble")

    @patch("scripts.service_router.run_cli")
    def test_wrap_callback_runs_wrap_sequence(self, run_cli) -> None:
        run_cli.side_effect = [
            ("freshness-pass", "", 0),
            ("finalize-pass", "", 0),
            ("sync-pass", "", 0),
            ("release-pass", "", 0),
        ]
        user_id = "test-wrap"
        confirm = route(RouteRequest(text="attn:wrap:attention_repo", user_id=user_id, platform="telegram"))
        self.assertIn("confirm-wrap@attention_repo", confirm.text)

        response = route(RouteRequest(text="attn:confirm-wrap:attention_repo", user_id=user_id, platform="telegram"))
        self.assertIn("released@attention_repo", response.text)
        self.assertIn("freshness-pass", response.text)
        self.assertIn("finalize-pass", response.text)
        self.assertIn("release-pass", response.text)
        self.assertEqual(response.structured_data["command"], "wrap")

    @patch("scripts.service_router.run_cli")
    def test_reinit_callback_requires_confirmation_and_executes(self, run_cli) -> None:
        run_cli.return_value = ("Recovery archive: /tmp/archive\nAuto-assemble: skipped", "", 0)
        user_id = "test-reinit"
        confirm = route(RouteRequest(text="/attention_repo reinit attention_repo", user_id=user_id, platform="telegram"))
        self.assertIn("confirm-reinit@attention_repo", confirm.text)

        response = route(RouteRequest(text="attn:confirm-reinit:attention_repo", user_id=user_id, platform="telegram"))
        self.assertIn("reinit@attention_repo", response.text)
        self.assertIn("Auto-assemble: skipped", response.text)
        self.assertEqual(response.structured_data["command"], "reinit")

    def test_list_projects_callback_shows_project_index(self) -> None:
        response = route(RouteRequest(text="attn:list-projects:", user_id="test-list", platform="telegram"))
        self.assertIn("choose a repo to start", response.text)
        self.assertTrue(response.suggest_menu)

    def test_main_menu_shows_active_attention_from_state_root(self) -> None:
        state_path = Path(self.state_root) / ".attention-state.json"
        state_path.write_text(
            json.dumps(
                {
                    "active": "attention_repo",
                    "active_path": str(self.project_root),
                    "attended_at": "2026-03-15T07:00:00+00:00",
                    "attended_repos": {},
                }
            ),
            encoding="utf-8",
        )

        response = route(RouteRequest(text="/attention_repo", user_id="test-main-menu", platform="telegram"))
        self.assertIn("Attending", response.text)
        self.assertIn("attention_repo", response.text)
        self.assertIn(str(self.project_root), response.text)

    def test_main_menu_gates_when_compiled_version_is_stale(self) -> None:
        state_path = Path(self.state_root) / "index.json"
        state_path.write_text(
            json.dumps(
                {
                    "version": "1",
                    "created_at": "2026-03-15T07:00:00+00:00",
                    "last_updated": "2026-03-15T07:00:00+00:00",
                    "projects": {},
                    "skill_runtime": {"compiled_version": "0.3.0"},
                }
            )
            + "\n",
            encoding="utf-8",
        )

        response = route(RouteRequest(text="/attention_repo", user_id="test-gate-menu", platform="telegram"))
        self.assertIn("bootstrap required", response.text.lower())
        self.assertIn("0.3.0", response.text)
        self.assertTrue(response.suggest_menu)

    @patch("scripts.service_router.run_cli")
    def test_bootstrap_update_action_executes_when_gate_is_active(self, run_cli) -> None:
        state_path = Path(self.state_root) / "index.json"
        state_path.write_text(
            json.dumps(
                {
                    "version": "1",
                    "created_at": "2026-03-15T07:00:00+00:00",
                    "last_updated": "2026-03-15T07:00:00+00:00",
                    "projects": {},
                    "skill_runtime": {"compiled_version": "0.3.0"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        run_cli.return_value = (
            f"Bootstrapped attention-repo control plane for v{get_version()}\nGate cleared: yes",
            "",
            0,
        )

        response = route(
            RouteRequest(text="attn:bootstrap-update:", user_id="test-bootstrap-update", platform="telegram")
        )

        self.assertIn("bootstrap complete", response.text.lower())
        self.assertIn("Gate cleared: yes", response.text)
        self.assertEqual(response.structured_data["command"], "bootstrap-update")

    @patch("scripts.service_router.run_cli")
    def test_global_attention_state_restores_follow_up_after_session_loss(self, run_cli) -> None:
        state_path = Path(self.state_root) / ".attention-state.json"
        state_path.write_text(
            json.dumps(
                {
                    "active": "attention_repo",
                    "active_path": str(self.project_root),
                    "attended_at": "2026-03-15T07:00:00+00:00",
                    "attended_repos": {},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        run_cli.side_effect = [
            ("task-saved", "", 0),
            ("assemble-complete", "", 0),
        ]

        response = route(
            RouteRequest(
                text="Fix Telegram persistence after process restart",
                user_id="test-global-resume",
                platform="telegram",
            )
        )

        self.assertIn("Saved your focus and refreshed project context.", response.text)
        self.assertEqual(run_cli.call_args_list[0].args[0], "update-task")
        self.assertEqual(run_cli.call_args_list[0].args[1], "attention_repo")
        self.assertEqual(run_cli.call_args_list[1].args[0], "assemble")

    def test_init_shows_registration_scan(self) -> None:
        skill_root = Path(self._tmpdir.name) / "workspace" / "skills" / "attention-repo"
        skill_root.mkdir(parents=True)
        (skill_root / "README.md").write_text("skill", encoding="utf-8")

        state_root_path = Path(self.state_root)
        with open(state_root_path / "config.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "$schema": "attention-repo-config-v3",
                    "paths": {
                        "default_scan_roots": [str(Path(self._tmpdir.name) / "workspace" / "projects")],
                        "optional_scan_roots": {"skills": str(Path(self._tmpdir.name) / "workspace" / "skills")},
                    },
                    "projects": {
                        "attention_repo": {
                            "canonical_path": str(self.project_root),
                            "source_strategy": "local_only",
                            "managed": True,
                            "source": "projects",
                            "scope": "projects",
                            "menu_visible": True,
                        }
                    },
                },
                handle,
            )

        response = route(RouteRequest(text="init", user_id="test-init", platform="telegram"))
        self.assertIn("Index New", response.text)
        self.assertIn("Reply `register <project-name>`, `register all`, or `cancel`.", response.text)
        self.assertIn("attention-repo", response.text)

    def test_init_dedupes_registered_repo_by_canonical_path(self) -> None:
        skill_root = Path(self._tmpdir.name) / "workspace" / "skills" / "attention-repo"
        skill_root.mkdir(parents=True)
        (skill_root / "README.md").write_text("skill", encoding="utf-8")

        state_root_path = Path(self.state_root)
        skills_root = Path(self._tmpdir.name) / "workspace" / "skills"
        projects_root = Path(self._tmpdir.name) / "workspace" / "projects"
        with open(state_root_path / "config.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "$schema": "attention-repo-config-v3",
                    "paths": {
                        "default_scan_roots": [str(projects_root)],
                        "optional_scan_roots": {"skills": str(skills_root)},
                    },
                    "projects": {
                        "attention_repo": {
                            "canonical_path": str(skill_root),
                            "source_strategy": "local_only",
                            "managed": True,
                            "source": "skills",
                            "scope": "skills",
                            "menu_visible": True,
                        }
                    },
                },
                handle,
            )

        response = route(RouteRequest(text="init", user_id="test-init-dedupe", platform="telegram"))
        self.assertIn("Already registered:", response.text)
        self.assertIn("attention-repo", response.text)
        self.assertIn("Unregistered: 0", response.text)

    def test_register_project_selection_registers_unregistered_repo(self) -> None:
        skill_root = Path(self._tmpdir.name) / "workspace" / "skills" / "attention-repo"
        skill_root.mkdir(parents=True)
        (skill_root / "README.md").write_text("skill", encoding="utf-8")

        state_root_path = Path(self.state_root)
        skills_root = Path(self._tmpdir.name) / "workspace" / "skills"
        projects_root = Path(self._tmpdir.name) / "workspace" / "projects"
        with open(state_root_path / "config.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "$schema": "attention-repo-config-v3",
                    "paths": {
                        "default_scan_roots": [str(projects_root)],
                        "optional_scan_roots": {"skills": str(skills_root)},
                    },
                    "projects": {
                        "attention_repo": {
                            "canonical_path": str(self.project_root),
                            "source_strategy": "local_only",
                            "managed": True,
                            "source": "projects",
                            "scope": "projects",
                            "menu_visible": True,
                        }
                    },
                },
                handle,
            )

        route(RouteRequest(text="init", user_id="test-register", platform="telegram"))
        response = route(RouteRequest(text="register attention-repo", user_id="test-register", platform="telegram"))
        self.assertIn("Registered:", response.text)
        self.assertIn("attention-repo", response.text)

        with open(state_root_path / "config.json", "r", encoding="utf-8") as handle:
            config = json.load(handle)
        self.assertEqual(config["projects"]["attention-repo"]["scope"], "skills")
        self.assertTrue((skill_root / "!MAP.md").exists())
        self.assertTrue((skill_root / "CURRENT_TASK.md").exists())

    def test_register_project_selection_rejects_unknown_name(self) -> None:
        skill_root = Path(self._tmpdir.name) / "workspace" / "skills" / "attention-repo"
        skill_root.mkdir(parents=True)
        (skill_root / "README.md").write_text("skill", encoding="utf-8")

        state_root_path = Path(self.state_root)
        skills_root = Path(self._tmpdir.name) / "workspace" / "skills"
        projects_root = Path(self._tmpdir.name) / "workspace" / "projects"
        with open(state_root_path / "config.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "$schema": "attention-repo-config-v3",
                    "paths": {
                        "default_scan_roots": [str(projects_root)],
                        "optional_scan_roots": {"skills": str(skills_root)},
                    },
                    "projects": {
                        "attention_repo": {
                            "canonical_path": str(self.project_root),
                            "source_strategy": "local_only",
                            "managed": True,
                            "source": "projects",
                            "scope": "projects",
                            "menu_visible": True,
                        }
                    },
                },
                handle,
            )

        route(RouteRequest(text="init", user_id="test-register-short", platform="telegram"))
        response = route(RouteRequest(text="register banana", user_id="test-register-short", platform="telegram"))
        self.assertIn("Unknown repo in current scan", response.text)

    def test_register_project_selection_accepts_register_all(self) -> None:
        skill_root = Path(self._tmpdir.name) / "workspace" / "skills" / "attention-repo"
        skill_root.mkdir(parents=True)
        (skill_root / "README.md").write_text("skill", encoding="utf-8")

        state_root_path = Path(self.state_root)
        skills_root = Path(self._tmpdir.name) / "workspace" / "skills"
        projects_root = Path(self._tmpdir.name) / "workspace" / "projects"
        with open(state_root_path / "config.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "$schema": "attention-repo-config-v3",
                    "paths": {
                        "default_scan_roots": [str(projects_root)],
                        "optional_scan_roots": {"skills": str(skills_root)},
                    },
                    "projects": {
                        "attention_repo": {
                            "canonical_path": str(self.project_root),
                            "source_strategy": "local_only",
                            "managed": True,
                            "source": "projects",
                            "scope": "projects",
                            "menu_visible": True,
                        }
                    },
                },
                handle,
            )

        route(RouteRequest(text="init", user_id="test-register-all", platform="telegram"))
        response = route(RouteRequest(text="register all", user_id="test-register-all", platform="telegram"))
        self.assertIn("Registered:", response.text)
        self.assertIn("attention-repo", response.text)

    def test_registration_scan_does_not_block_normal_commands(self) -> None:
        skill_root = Path(self._tmpdir.name) / "workspace" / "skills" / "attention-repo"
        skill_root.mkdir(parents=True)
        (skill_root / "README.md").write_text("skill", encoding="utf-8")

        state_root_path = Path(self.state_root)
        skills_root = Path(self._tmpdir.name) / "workspace" / "skills"
        projects_root = Path(self._tmpdir.name) / "workspace" / "projects"
        with open(state_root_path / "config.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "$schema": "attention-repo-config-v3",
                    "paths": {
                        "default_scan_roots": [str(projects_root)],
                        "optional_scan_roots": {"skills": str(skills_root)},
                    },
                    "projects": {
                        "attention_repo": {
                            "canonical_path": str(self.project_root),
                            "source_strategy": "local_only",
                            "managed": True,
                            "source": "projects",
                            "scope": "projects",
                            "menu_visible": True,
                        }
                    },
                },
                handle,
            )

        route(RouteRequest(text="init", user_id="test-registration-latch", platform="telegram"))
        response = route(RouteRequest(text="projects", user_id="test-registration-latch", platform="telegram"))
        self.assertIn("choose a repo to start", response.text)
        self.assertNotIn("Reply with `register <project-name>`", response.text)

    def test_format_for_telegram_labels_skill_scope(self) -> None:
        skill_root = Path(self._tmpdir.name) / "workspace" / "skills" / "attention-repo"
        skill_root.mkdir(parents=True)
        (skill_root / "!MAP.md").write_text("# !MAP.md\n", encoding="utf-8")
        (skill_root / "CURRENT_TASK.md").write_text("# CURRENT_TASK.md\n\nIdle.\n", encoding="utf-8")

        state_root_path = Path(self.state_root)
        with open(state_root_path / "config.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "$schema": "attention-repo-config-v3",
                    "paths": {
                        "default_scan_roots": [str(Path(self._tmpdir.name) / "workspace" / "projects")],
                        "optional_scan_roots": {"skills": str(Path(self._tmpdir.name) / "workspace" / "skills")},
                    },
                    "projects": {
                        "attention_repo": {
                            "canonical_path": str(self.project_root),
                            "source_strategy": "local_only",
                            "managed": True,
                            "source": "projects",
                            "scope": "projects",
                            "menu_visible": True,
                        },
                        "attention-repo": {
                            "canonical_path": str(skill_root),
                            "source_strategy": "local_only",
                            "managed": True,
                            "source": "skills",
                            "scope": "skills",
                            "menu_visible": True,
                        },
                    },
                },
                handle,
            )

        payload = route(RouteRequest(text="attn:list-projects:", user_id="test-labels", platform="telegram"))
        skill_labels = [item["label"] for item in payload.menu_items]
        self.assertIn("📋 attention_repo", skill_labels)
        self.assertIn("🧰 attention-repo", skill_labels)

    def test_bridge_rewrites_router_callbacks_into_plugin_commands(self) -> None:
        rewritten = _rewrite_buttons(
            [
                [
                    {"text": "Projects", "callback_data": "attn:list-projects:"},
                    {"text": "Index New", "callback_data": "attn:init:"},
                ]
            ]
        )
        self.assertEqual(
            rewritten,
            [
                [
                    {"text": "Projects", "callback_data": "/attention_repo attn:list-projects:"},
                    {"text": "Index New", "callback_data": "/attention_repo attn:init:"},
                ]
            ],
        )


if __name__ == "__main__":
    unittest.main()
