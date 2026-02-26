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
