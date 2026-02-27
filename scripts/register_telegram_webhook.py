"""
One-time script to register the Lambda Function URL as the Telegram webhook.

Usage:
    .venv/Scripts/python scripts/register_telegram_webhook.py

Requirements:
    - TELEGRAM_BOT_TOKEN set in .env
    - python-dotenv installed in venv

The script will:
    1. Read bot token from .env
    2. Call setWebhook with the Lambda Function URL + secret_token
    3. Call getWebhookInfo to confirm registration
    4. Print the secret token (store it as TELEGRAM_WEBHOOK_SECRET Lambda env var)
"""

import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Load .env from project root
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    print("⚠️  python-dotenv not installed — reading env vars directly")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
FUNCTION_URL = "https://gcquxmfbpd7lbty3m4jp7cki6m0xaubd.lambda-url.us-east-1.on.aws/"

_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _call(method: str, payload: dict | None = None) -> dict:
    url  = f"{_BASE}/{method}"
    data = json.dumps(payload or {}).encode("utf-8") if payload else None
    req  = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    print(f"Bot token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-6:]}")
    print(f"Webhook URL: {FUNCTION_URL}")

    # Generate a random secret token for webhook verification
    secret_token = secrets.token_hex(32)
    print(f"\nGenerated webhook secret token: {secret_token}")
    print("  -> Add this to Lambda env var: TELEGRAM_WEBHOOK_SECRET")

    # Register webhook
    print("\nCalling setWebhook...")
    try:
        result = _call("setWebhook", {
            "url": FUNCTION_URL,
            "allowed_updates": ["message"],
            "secret_token": secret_token,
        })
        if result.get("ok"):
            print(f"[OK] Webhook set: {result.get('description', 'OK')}")
        else:
            print(f"[FAIL] setWebhook failed: {result}")
            sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"[FAIL] HTTP error: {e.code} {e.reason}")
        print(e.read().decode())
        sys.exit(1)

    # Confirm registration
    print("\nCalling getWebhookInfo...")
    try:
        info = _call("getWebhookInfo")
        webhook = info.get("result", {})
        print(f"   URL:              {webhook.get('url')}")
        print(f"   Has custom cert:  {webhook.get('has_custom_certificate')}")
        print(f"   Pending updates:  {webhook.get('pending_update_count', 0)}")
        print(f"   Allowed updates:  {webhook.get('allowed_updates', [])}")
        last_error = webhook.get("last_error_message")
        if last_error:
            print(f"   Last error:       {last_error}")
            print(f"       at:           {webhook.get('last_error_date')}")
    except Exception as e:
        print(f"WARNING: Could not retrieve webhook info: {e}")

    print("\n[DONE] Next steps:")
    print(f"   1. Add to Lambda env var:  TELEGRAM_WEBHOOK_SECRET={secret_token}")
    print("   2. Deploy Lambda: .venv/Scripts/python infra/setup.py --step lambdas")
    print("   3. Send /start to your bot to test")


if __name__ == "__main__":
    main()
