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
        self.project_root = Path(self._tmpdir.name) / "workspace" / "projects" / "attention_layer"
        self.project_root.mkdir(parents=True)
        (self.project_root / "!MAP.md").write_text("# !MAP.md\n", encoding="utf-8")
        (self.project_root / "CURRENT_TASK.md").write_text(
            "# CURRENT_TASK.md\n\nIn progress: stabilize Telegram menu flow.\n",
            encoding="utf-8",
        )
        state_root_path = Path(self.state_root)
        state_root_path.mkdir(parents=True)
        with open(state_root_path / "config.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "$schema": "attention-layer-config-v2",
                    "projects": {
                        "attention_layer": {
                            "canonical_path": str(self.project_root),
                            "source_strategy": "local_only",
                            "managed": True,
                            "source": "test",
                        }
                    },
                },
                handle,
            )
        self._env = patch.dict(
            os.environ,
            {
                "ATTENTION_LAYER_STATE_ROOT": self.state_root,
                "OPENCLAW_CONFIG_PATH": self.openclaw_config_path,
            },
        )
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()
        self._tmpdir.cleanup()

    def test_start_callback_shows_latest_task_summary(self) -> None:
        response = route(RouteRequest(text="attn:start:attention_layer", user_id="test-start", platform="telegram"))
        self.assertIn("Start attention_layer", response.text)
        self.assertIn("Latest task summary", response.text)
        self.assertIn("stabilize Telegram menu flow", response.text)

    @patch("scripts.service_router.run_cli")
    def test_follow_up_message_updates_task_after_start(self, run_cli) -> None:
        run_cli.side_effect = [
            ("task-updated", "", 0),
            ("assemble-ok", "", 0),
        ]
        user_id = "test-follow-up"
        first = route(RouteRequest(text="attn:start:attention_layer", user_id=user_id, platform="telegram"))
        self.assertIn("Reply with the next task", first.text)

        second = route(
            RouteRequest(
                text="Fix auth callback redirect and clean stale buttons",
                user_id=user_id,
                platform="telegram",
            )
        )
        self.assertIn("Declared current focus and refreshed the project map.", second.text)
        self.assertEqual(second.structured_data["command"], "start")
        self.assertEqual(run_cli.call_args_list[0].args[0], "update-task")
        self.assertEqual(run_cli.call_args_list[1].args[0], "assemble")

    @patch("scripts.service_router.run_cli")
    def test_wrap_callback_runs_wrap_sequence(self, run_cli) -> None:
        run_cli.side_effect = [
            ("freshness-ok", "", 0),
            ("finalize-ok", "", 0),
            ("sync-ok", "", 0),
        ]
        response = route(RouteRequest(text="attn:wrap:attention_layer", user_id="test-wrap", platform="telegram"))
        self.assertIn("Wrap Up attention_layer", response.text)
        self.assertIn("freshness-ok", response.text)
        self.assertIn("finalize-ok", response.text)
        self.assertEqual(response.structured_data["command"], "wrap")

    def test_list_projects_callback_shows_project_index(self) -> None:
        response = route(RouteRequest(text="attn:list-projects:", user_id="test-list", platform="telegram"))
        self.assertIn("choose a repo to start", response.text)
        self.assertTrue(response.suggest_menu)

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
                    {"text": "Projects", "callback_data": "/attention_layer attn:list-projects:"},
                    {"text": "Index New", "callback_data": "/attention_layer attn:init:"},
                ]
            ],
        )


if __name__ == "__main__":
    unittest.main()
