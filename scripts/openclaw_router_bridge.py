#!/usr/bin/env python3
"""Bridge OpenClaw plugin commands to the Python service router."""

from __future__ import annotations

import argparse
import json
import sys

try:
    from scripts.service_router import RouteRequest, handle
except ModuleNotFoundError:
    from service_router import RouteRequest, handle


def _rewrite_buttons(button_rows: list[list[dict]]) -> list[list[dict]]:
    """Rewrite router callback payloads into plugin command callback payloads."""
    rewritten: list[list[dict]] = []
    for row in button_rows:
        next_row: list[dict] = []
        for button in row:
            callback_data = str(button.get("callback_data", "")).strip()
            if callback_data:
                callback_data = f"/attention_layer {callback_data}"
            next_row.append(
                {
                    "text": str(button.get("text", "")),
                    "callback_data": callback_data,
                }
            )
        rewritten.append(next_row)
    return rewritten


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", required=True, help="Full command text to route")
    parser.add_argument("--user-id", required=True, help="Stable sender ID")
    parser.add_argument("--platform", default="telegram", help="Origin platform")
    parser.add_argument("--chat-type", default="direct", help="Chat type")
    parser.add_argument("--message-id", default=None, help="Message identifier")
    parser.add_argument("--reply-to", default=None, help="Reply target identifier")
    args = parser.parse_args()

    payload = handle(
        RouteRequest(
            text=args.text,
            user_id=args.user_id,
            platform=args.platform,
            chat_type=args.chat_type,
            message_id=args.message_id,
            reply_to=args.reply_to,
        )
    )

    result = {"text": str(payload.get("text", ""))}
    button_rows = ((payload.get("reply_markup") or {}).get("inline_keyboard")) or []
    if button_rows:
        result["channelData"] = {"telegram": {"buttons": _rewrite_buttons(button_rows)}}

    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
