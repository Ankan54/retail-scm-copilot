"""
Shared PostgreSQL database utilities for SupplyChain Copilot Lambda functions.
Replaces the previous SQLite + S3 approach with direct RDS PostgreSQL connections.
"""

import os
import json
import logging
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Connection config from Lambda env vars ────────────────────────────────────
DB_HOST     = os.environ.get("DB_HOST", "")
DB_PORT     = int(os.environ.get("DB_PORT", "5432"))
DB_NAME     = os.environ.get("DB_NAME", "supplychain")
DB_USER     = os.environ.get("DB_USER", "scm_admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_SSL      = os.environ.get("DB_SSL", "require")  # require for RDS

# Lazy import — psycopg2 is bundled in the Lambda zip
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # Will error at connect time with helpful message


# ─── Connection helper ────────────────────────────────────────────────────────

def get_db():
    """
    Get a new psycopg2 connection to RDS PostgreSQL.
    Connection is NOT cached across Lambda invocations (Lambda is stateless).
    autocommit=False — callers must explicitly commit/rollback.
    Cursor uses RealDictCursor so rows behave like dicts.
    """
    if psycopg2 is None:
        raise RuntimeError("psycopg2 not available — check Lambda zip packaging")

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        sslmode=DB_SSL,
        connect_timeout=10,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.autocommit = False
    return conn


# ─── Date helpers ─────────────────────────────────────────────────────────────

def today() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.utcnow().isoformat()


# ─── Row helpers ──────────────────────────────────────────────────────────────

def row_to_dict(row) -> Optional[dict]:
    """Convert a psycopg2 RealDictRow (or None) to a plain dict."""
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows) -> list:
    """Convert a list of psycopg2 RealDictRow objects to a list of dicts."""
    return [dict(r) for r in rows]


def _serialize(obj):
    """JSON serializer for types not serializable by default (dates, Decimals)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    try:
        import decimal
        if isinstance(obj, decimal.Decimal):
            return float(obj)
    except ImportError:
        pass
    raise TypeError(f"Type {type(obj)} not serializable")


# ─── Session helpers (replaces DynamoDB) ─────────────────────────────────────

def get_session(telegram_chat_id: str) -> Optional[dict]:
    """Retrieve an active session by telegram_chat_id."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT session_id, sales_person_id, agent_session_id, context, last_message
            FROM sessions
            WHERE telegram_chat_id = %s
              AND expires_at > NOW()
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (telegram_chat_id,),
        )
        row = cur.fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def save_session(telegram_chat_id: str, sales_person_id: str,
                 agent_session_id: str, context: dict = None,
                 last_message: str = "") -> str:
    """Upsert a session. Returns session_id."""
    import uuid
    conn = get_db()
    try:
        cur = conn.cursor()
        # Check if session exists
        cur.execute(
            "SELECT session_id FROM sessions WHERE telegram_chat_id = %s AND expires_at > NOW()",
            (telegram_chat_id,),
        )
        existing = cur.fetchone()

        ctx_json = json.dumps(context or {})
        if existing:
            session_id = existing["session_id"]
            cur.execute(
                """
                UPDATE sessions
                SET sales_person_id = %s, agent_session_id = %s, context = %s,
                    last_message = %s, updated_at = NOW(),
                    expires_at = NOW() + INTERVAL '24 hours'
                WHERE session_id = %s
                """,
                (sales_person_id, agent_session_id, ctx_json, last_message, session_id),
            )
        else:
            session_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO sessions
                    (session_id, telegram_chat_id, sales_person_id, agent_session_id,
                     context, last_message, created_at, updated_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW() + INTERVAL '24 hours')
                """,
                (session_id, telegram_chat_id, sales_person_id,
                 agent_session_id, ctx_json, last_message),
            )
        conn.commit()
        return session_id
    finally:
        conn.close()


# ─── Bedrock Agent response formatter ─────────────────────────────────────────

def get_web_session(session_id: str) -> Optional[dict]:
    """Retrieve a web chat session by session_id (source='web')."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT session_id, agent_session_id, messages, title, last_message
            FROM sessions
            WHERE session_id = %s
              AND source = 'web'
              AND expires_at > NOW()
            """,
            (session_id,),
        )
        row = cur.fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def save_web_session(session_id: str, agent_session_id: str,
                     messages: list, title: str = "New Conversation",
                     last_message: str = "") -> str:
    """Upsert a web chat session. Returns session_id."""
    conn = get_db()
    try:
        cur = conn.cursor()
        msgs_json = json.dumps(messages, default=_serialize)
        cur.execute(
            """
            INSERT INTO sessions
                (session_id, telegram_chat_id, sales_person_id, agent_session_id,
                 context, last_message, messages, title, source,
                 created_at, updated_at, expires_at)
            VALUES (%s, NULL, NULL, %s, '{}', %s, %s::jsonb, %s, 'web',
                    NOW(), NOW(), NOW() + INTERVAL '7 days')
            ON CONFLICT (session_id) DO UPDATE SET
                agent_session_id = EXCLUDED.agent_session_id,
                last_message = EXCLUDED.last_message,
                messages = EXCLUDED.messages,
                title = EXCLUDED.title,
                updated_at = NOW(),
                expires_at = NOW() + INTERVAL '7 days'
            """,
            (session_id, agent_session_id, last_message, msgs_json, title),
        )
        conn.commit()
        return session_id
    finally:
        conn.close()


# ─── Telegram sales rep helpers ───────────────────────────────────────────────

def lookup_sales_person_by_telegram(telegram_user_id: str) -> Optional[dict]:
    """Look up a sales rep by their Telegram user ID. Returns the row or None."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT sales_person_id, name, employee_code, role,
                   telegram_user_id, telegram_chat_id
            FROM sales_persons
            WHERE telegram_user_id = %s AND is_active = TRUE
            LIMIT 1
            """,
            (telegram_user_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def register_telegram_user(employee_code: str, telegram_user_id: str,
                            telegram_chat_id: str) -> Optional[dict]:
    """
    Link a Telegram user to a sales rep by employee code.
    Returns the updated row (name, role, sales_person_id) or None if not found.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE sales_persons
            SET telegram_user_id = %s, telegram_chat_id = %s, updated_at = NOW()
            WHERE employee_code = %s AND is_active = TRUE
            RETURNING sales_person_id, name, role, employee_code
            """,
            (telegram_user_id, telegram_chat_id, employee_code.upper()),
        )
        row = cur.fetchone()
        if row:
            conn.commit()
        return row_to_dict(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_manager_telegram_chat_id() -> Optional[str]:
    """Return the Telegram chat_id of the manager, or None if not set."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT telegram_chat_id
            FROM sales_persons
            WHERE role = 'MANAGER' AND is_active = TRUE
            LIMIT 1
            """,
        )
        row = cur.fetchone()
        if row and row["telegram_chat_id"]:
            return str(row["telegram_chat_id"])
        return None
    finally:
        conn.close()


def mark_alert_sent(alert_id: str) -> None:
    """Mark an alert row as notification_sent=TRUE via Telegram."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE alerts
            SET notification_sent = TRUE,
                notification_channel = 'telegram',
                notification_sent_at = NOW(),
                updated_at = NOW()
            WHERE alert_id = %s
            """,
            (alert_id,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def bedrock_response(action_group: str, function: str, result: dict) -> dict:
    """Format a response for the Bedrock Agent action group protocol."""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function,
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": json.dumps(result, default=_serialize)
                    }
                }
            },
        },
    }
