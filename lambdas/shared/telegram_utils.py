"""
Telegram Bot API utilities for SupplyChain Copilot.
Uses stdlib urllib.request — no extra dependencies required.
"""

import json
import logging
import os
import urllib.request
import urllib.parse
import urllib.error

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

_BASE = "https://api.telegram.org/bot"


try:
    import telegramify_markdown
    _TELEGRAMIFY_AVAILABLE = True
except ImportError:
    _TELEGRAMIFY_AVAILABLE = False
    logger.warning("telegramify-markdown not installed — messages sent as plain text")


def _api_url(method: str) -> str:
    return f"{_BASE}{BOT_TOKEN}/{method}"


def _post(method: str, payload: dict) -> bool:
    """POST JSON payload to a Telegram Bot API method. Returns True on success."""
    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — skipping Telegram call")
        return False
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            _api_url(method),
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if not body.get("ok"):
                logger.warning(f"Telegram {method} not ok: {body}")
            return bool(body.get("ok"))
    except urllib.error.URLError as e:
        logger.error(f"Telegram {method} network error: {e}")
        return False
    except Exception as e:
        logger.error(f"Telegram {method} error: {e}")
        return False


def parse_telegram_update(body: dict) -> dict | None:
    """
    Parse an incoming Telegram Update dict.
    Returns {chat_id, user_id, text, first_name, username} or None if not a message.
    """
    if "update_id" not in body:
        return None
    msg = body.get("message") or body.get("edited_message")
    if not msg:
        return None
    chat = msg.get("chat", {})
    user = msg.get("from", {})
    return {
        "chat_id": str(chat.get("id", "")),
        "user_id": str(user.get("id", "")),
        "text": (msg.get("text") or "").strip(),
        "first_name": user.get("first_name", ""),
        "username": user.get("username", ""),
    }


def send_message(chat_id: str | int, text: str, parse_mode: str = "MarkdownV2") -> bool:
    """
    Send a text message to a Telegram chat. Returns True on success.
    Uses telegramify-markdown to convert LLM Markdown output to MarkdownV2.
    Falls back to plain text (no parse_mode) if library is unavailable.
    """
    if not text:
        return False
    if _TELEGRAMIFY_AVAILABLE:
        text = telegramify_markdown.markdownify(text)
    else:
        parse_mode = None
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    return _post("sendMessage", payload)


def send_typing_action(chat_id: str | int) -> bool:
    """Send a 'typing...' indicator to a Telegram chat. Expires after ~5 seconds."""
    return _post("sendChatAction", {
        "chat_id": chat_id,
        "action": "typing",
    })


def validate_secret_token(event: dict, expected_token: str) -> bool:
    """
    Validate the X-Telegram-Bot-Api-Secret-Token header.
    Returns True if the header matches expected_token (or if expected_token is empty).
    """
    if not expected_token:
        return True
    headers = event.get("headers") or {}
    # Header names may be lowercased by API Gateway / Lambda Function URL
    received = (
        headers.get("X-Telegram-Bot-Api-Secret-Token")
        or headers.get("x-telegram-bot-api-secret-token")
        or ""
    )
    return received == expected_token
