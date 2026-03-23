#!/usr/bin/env python3
"""
Telegram bot handler for attention_repo skill.

THIN wrapper around service_router.py. No business logic here.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Add skill scripts to path for import
_SKILL_ROOT = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(_SKILL_ROOT / "scripts"))

from service_router import handle, RouteRequest


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED_USER_IDS = set(
    filter(None, os.environ.get("ATTENTION_TELEGRAM_USERS", "").split(","))
)
TELEGRAM_BOT_TOKEN = os.environ.get("ATTENTION_TELEGRAM_BOT_TOKEN", "")


# ─────────────────────────────────────────────────────────────────────────────
# Telegram Interface
# ─────────────────────────────────────────────────────────────────────────────

def is_authorized(user_id: str) -> bool:
    """Check if user is in allowlist."""
    if not ALLOWED_USER_IDS:
        return True  # No allowlist = allow all (dev only)
    return user_id in ALLOWED_USER_IDS


def format_telegram_payload(response: dict) -> dict:
    """Format service_router response for Telegram API."""
    payload = {
        "text": response.get("text", "No response"),
        "parse_mode": response.get("parse_mode", "Markdown"),
    }
    
    # Add inline keyboard if present
    if response.get("reply_markup"):
        payload["reply_markup"] = response["reply_markup"]
    
    return payload


def handle_telegram_message(chat_id: str, user_id: str, text: str) -> dict:
    """Handle incoming Telegram message."""
    if not is_authorized(user_id):
        return {"chat_id": chat_id, "text": "⛔ Not authorized"}
    
    # Strip /attention or /attention_repo prefix if present
    if text.startswith(("/attention_repo", "/attention ", "!attention ")):
        if text.startswith("/attention_repo"):
            text = text[len("/attention_repo"):].strip()
        else:
            text = text.split(None, 1)[1] if " " in text else ""
    
    # Route via service_router
    request = RouteRequest(
        text=text,
        user_id=user_id,
        platform="telegram",
        chat_type="direct"
    )
    
    response = handle(request)
    
    # Format for Telegram
    payload = format_telegram_payload(response)
    payload["chat_id"] = chat_id
    
    return payload


def handle_telegram_callback(chat_id: str, user_id: str, callback_data: str) -> dict:
    """Handle Telegram callback query."""
    if not is_authorized(user_id):
        return {"chat_id": chat_id, "text": "⛔ Not authorized"}
    
    # Pass callback payload through as-is; service_router owns callback semantics.
    text = callback_data
    
    # Route via service_router
    request = RouteRequest(
        text=text,
        user_id=user_id,
        platform="telegram",
        chat_type="direct"
    )
    
    response = handle(request)
    payload = format_telegram_payload(response)
    payload["chat_id"] = chat_id
    
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# Example Integration (python-telegram-bot)
# ─────────────────────────────────────────────────────────────────────────────

"""
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

async def attention_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    payload = handle_telegram_message(chat_id, user_id, text)
    
    await context.bot.send_message(
        chat_id=payload["chat_id"],
        text=payload["text"],
        parse_mode=payload.get("parse_mode"),
        reply_markup=InlineKeyboardMarkup(payload.get("reply_markup", {}).get("inline_keyboard", []))
        if payload.get("reply_markup") else None
    )

async def attention_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    callback_data = query.data
    
    payload = handle_telegram_callback(chat_id, user_id, callback_data)
    
    await query.edit_message_text(
        text=payload["text"],
        parse_mode=payload.get("parse_mode"),
        reply_markup=InlineKeyboardMarkup(payload.get("reply_markup", {}).get("inline_keyboard", []))
        if payload.get("reply_markup") else None
    )

# Setup
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("attention_repo", attention_command))
app.add_handler(CallbackQueryHandler(attention_callback, pattern="^attn:"))
app.run_polling()
"""


# ─────────────────────────────────────────────────────────────────────────────
# Test CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    print("Telegram Handler Test (using service_router)")
    print("=" * 50)
    
    # Test 1: /attention command - shows index menu
    print("\n1. User: /attention_repo")
    print("   Expected: Show project index menu (fast, no !MAP.md reads)")
    result = handle_telegram_message("12345", "user-1", "/attention_repo")
    print(f"   Bot: {result['text'][:80]}...")
    
    # Test 2: Select project - click Projects button, then choose project
    print("\n2. User: [clicks Projects button] → list-projects")
    print("   Expected: Show registered projects")
    result = handle_telegram_message("12345", "user-1", "list-projects")
    print(f"   Bot: {result['text'][:60]}...")
    
    # Test 3: Select action - intent declaration (confirmation required)
    print("\n3. User: [clicks assemble] → assemble summon-A2A-academy")
    print("   Expected: Intent declaration with confirmation (NOT executing yet)")
    result = handle_telegram_message("12345", "user-2", "/attention assemble summon-A2A-academy")
    print(f"   Bot: {result['text'][:80]}...")
    
    # Test 4: Confirm action - now executes
    print("\n4. User: 'yes' (confirming)")
    print("   Expected: Execute and read !MAP.md")
    result = handle_telegram_message("12345", "user-2", "yes")
    print(f"   Bot: {result['text'][:80]}...")
