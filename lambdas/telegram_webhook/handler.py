"""
Chat Lambda Handler — Bedrock Supervisor Agent invocation (BUFFERED mode).

Dual routing:
  - Telegram webhook updates  → sales rep bot (identity resolved from DB)
  - Dashboard requests        → manager chat (source='dashboard')

Telegram flow:
  1. Parse update, lookup user by telegram_user_id in DB
  2. If unknown → registration flow (ask for employee code)
  3. If MANAGER role → manager context
  4. If REP role    → rep context (get_sales_rep first)
  5. Send typing, invoke Bedrock, reply via Telegram
  6. Save session (24h expiry for Telegram, 7d for web)

Dashboard flow (unchanged):
  - source='dashboard' → manager context injected
  - Returns buffered JSON for frontend animation
"""
import json
import logging
import os
import sys
import uuid
import time

import boto3

sys.path.insert(0, "/opt/python")
sys.path.insert(0, "/var/task")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AGENT_ID       = os.environ.get("BEDROCK_AGENT_ID", "")
AGENT_ALIAS_ID = os.environ.get("BEDROCK_AGENT_ALIAS_ID", "")
REGION         = os.environ.get("REGION", "us-east-1")

# Webhook secret token for verifying Telegram requests (set during webhook registration)
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
}


# ─── Context builders ─────────────────────────────────────────────────────────

def _build_manager_context(telegram_user_id: str, message: str) -> str:
    return (
        f"[MANAGER DASHBOARD QUERY]\n"
        f"Caller: telegram_user_id={telegram_user_id}, role=MANAGER\n"
        f"Scope: This query is from the Sales/Production Manager. "
        f"Return company-wide aggregated results across ALL sales reps and territories. "
        f"Do NOT filter by individual sales rep. Show collective team and business performance.\n"
        f"---\n"
        f"{message}"
    )


def _build_rep_context(telegram_user_id: str, message: str) -> str:
    return (
        f"[SALES REP QUERY]\n"
        f"Caller: telegram_user_id={telegram_user_id}, role=REP\n"
        f"Scope: First call get_sales_rep with telegram_user_id={telegram_user_id} "
        f"to resolve sales_person_id. "
        f"All results must be specific to this rep. Never use Manager_Analytics_Agent.\n"
        f"---\n"
        f"{message}"
    )


# ─── Bedrock helpers ──────────────────────────────────────────────────────────

def _get_bedrock_client():
    return boto3.client("bedrock-agent-runtime", region_name=REGION)


def _log_truncated(label: str, value, max_len: int = 300):
    if isinstance(value, (dict, list)):
        s = json.dumps(value, default=str)
    else:
        s = str(value)
    if len(s) > max_len:
        s = s[:max_len] + f"... [{len(s)} chars total]"
    logger.info(f"{label}: {s}")


def _invoke_agent(message: str, session_id: str, context=None) -> dict:
    """
    Invoke the Bedrock Supervisor Agent.
    Returns { text, agent, session_id, traces[] }.
    """
    logger.info(
        f"🚀 Starting agent invocation | Session: {session_id} | "
        f"AgentID: {AGENT_ID} | Alias: {AGENT_ALIAS_ID}"
    )
    _log_truncated("📝 User message", message, 500)

    start_time = time.time()
    client = _get_bedrock_client()

    try:
        response = client.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=message,
            enableTrace=True,
        )
    except Exception as e:
        logger.error(f"❌ invoke_agent failed: {type(e).__name__}: {e}", exc_info=True)
        raise

    full_text  = ""
    agent_name = "Supervisor"
    traces     = []
    event_count = 0
    error_count = 0

    for event in response["completion"]:
        event_count += 1
        elapsed = time.time() - start_time

        if context and hasattr(context, "get_remaining_time_in_millis"):
            if context.get_remaining_time_in_millis() < 15000:
                logger.warning(f"⏰ [{elapsed:.2f}s] LOW TIME WARNING")

        if "chunk" in event:
            chunk = event["chunk"]
            if "bytes" in chunk:
                text = chunk["bytes"].decode("utf-8")
                full_text += text
                logger.info(f"💬 [{elapsed:.2f}s] CHUNK ({len(text)} chars): {text[:120].replace(chr(10),' ')}")

        if "trace" in event:
            trace = event["trace"].get("trace", {})
            orch  = trace.get("orchestrationTrace", {})

            invocation_input = orch.get("invocationInput", {})

            collab = invocation_input.get("agentCollaboratorInvocationInput", {})
            if collab.get("agentCollaboratorName"):
                agent_name = collab["agentCollaboratorName"].replace("_", " ")
                logger.info(f"🤖 [{elapsed:.2f}s] ROUTING → {agent_name}")
                traces.append({"type": "agent", "step": f"Routing to {agent_name}...", "agent": agent_name})

            action_group = invocation_input.get("actionGroupInvocationInput", {})
            if action_group.get("function"):
                tool_name = action_group["function"]
                params = {p["name"]: p.get("value") for p in action_group.get("parameters", [])}
                logger.info(f"🔧 [{elapsed:.2f}s] TOOL CALL: {tool_name}")
                _log_truncated(f"   ↳ params", params)
                traces.append({"type": "tool", "step": f"Calling {tool_name}...", "tool": tool_name})

            code_interp = invocation_input.get("codeInterpreterInvocationInput", {})
            if code_interp:
                logger.info(f"🧮 [{elapsed:.2f}s] CODE INTERPRETER")
                traces.append({"type": "tool", "step": "Running calculation...", "tool": "CodeInterpreter"})

            observation = orch.get("observation", {})
            if observation:
                obs_type = observation.get("type", "unknown")
                ag_out   = observation.get("actionGroupInvocationOutput", {})
                if ag_out:
                    _log_truncated(f"👁️  [{elapsed:.2f}s] TOOL RESPONSE ({obs_type})", ag_out.get("text", ""))
                collab_out = observation.get("agentCollaboratorInvocationOutput", {})
                if collab_out:
                    _log_truncated(f"👁️  [{elapsed:.2f}s] AGENT RESPONSE from {collab_out.get('agentCollaboratorName','?')}", collab_out.get("output", {}))
                ci_out = observation.get("codeInterpreterInvocationOutput", {})
                if ci_out:
                    _log_truncated(f"👁️  [{elapsed:.2f}s] CODE OUTPUT", ci_out)
                if not ag_out and not collab_out and not ci_out:
                    logger.info(f"👁️  [{elapsed:.2f}s] OBSERVATION: {obs_type}")

            rationale = orch.get("rationale", {})
            if rationale.get("text"):
                _log_truncated(f"💭 [{elapsed:.2f}s] THINKING", rationale["text"], 400)

            failure = trace.get("failureTrace", {})
            if failure:
                error_count += 1
                logger.error(f"❌ [{elapsed:.2f}s] FAILURE TRACE: {json.dumps(failure, default=str)}")

    total_time = time.time() - start_time
    logger.info(
        f"✅ Invocation complete | Time: {total_time:.2f}s | Events: {event_count} | "
        f"Errors: {error_count} | Agent: {agent_name} | Response: {len(full_text)} chars"
    )
    if full_text:
        _log_truncated("📤 Final response", full_text, 500)

    return {
        "text": full_text.strip() or "I'm sorry, I couldn't generate a response. Please try again.",
        "agent": agent_name,
        "session_id": session_id,
        "traces": traces,
    }


# ─── Session persistence ──────────────────────────────────────────────────────

def _save_web_session(session_id: str, agent_session_id: str,
                      user_msg: str, assistant_msg: dict):
    """Persist a web dashboard chat turn to PostgreSQL."""
    try:
        from shared.db_utils import get_web_session, save_web_session

        existing  = get_web_session(session_id)
        messages  = []
        if existing and existing.get("messages"):
            messages = existing["messages"]
            if isinstance(messages, str):
                messages = json.loads(messages)

        messages.append({"role": "user", "text": user_msg})
        messages.append({
            "role": "assistant",
            "text": assistant_msg["text"],
            "agent": assistant_msg["agent"],
        })

        title = existing.get("title", "New Conversation") if existing else user_msg[:36]
        save_web_session(
            session_id=session_id,
            agent_session_id=agent_session_id,
            messages=messages,
            title=title,
            last_message=user_msg,
        )
        logger.info(f"💾 Web session saved | Session: {session_id}")
    except Exception as e:
        logger.warning(f"⚠️  Failed to save web session: {e}")


def _save_telegram_session(chat_id: str, sales_person_id: str,
                           agent_session_id: str, last_message: str):
    """Persist a Telegram chat session (24-hour expiry)."""
    try:
        from shared.db_utils import save_session
        save_session(
            telegram_chat_id=chat_id,
            sales_person_id=sales_person_id or "",
            agent_session_id=agent_session_id,
            last_message=last_message,
        )
        logger.info(f"💾 Telegram session saved | chat_id: {chat_id}")
    except Exception as e:
        logger.warning(f"⚠️  Failed to save Telegram session: {e}")


# ─── Telegram: fast handlers (sync — no Bedrock) ─────────────────────────────

def _handle_telegram_fast(body: dict) -> dict | None:
    """
    Handle fast Telegram operations synchronously (no Bedrock needed).
    Returns a response dict if handled, or None if the message needs Bedrock.
    """
    from shared.telegram_utils import parse_telegram_update, send_message
    from shared.db_utils import (
        lookup_sales_person_by_telegram, register_telegram_user,
    )

    update = parse_telegram_update(body)
    if not update:
        return {"statusCode": 200, "body": "ok"}

    chat_id = update["chat_id"]
    user_id = update["user_id"]
    text    = update["text"]
    name    = update["first_name"] or "there"

    logger.info(f"📲 Telegram update | user_id={user_id} chat_id={chat_id} text={text[:80]!r}")

    # ── /start command ────────────────────────────────────────────────────────
    if text.lower() == "/start":
        person = lookup_sales_person_by_telegram(user_id)
        if person:
            role_label = "Manager" if person["role"] == "MANAGER" else "Sales Rep"
            send_message(chat_id,
                f"Welcome back, **{person['name']}**! ({role_label})\n\n"
                f"How can I help you today?")
        else:
            send_message(chat_id,
                f"Hello, **{name}**! Welcome to CleanMax SupplyChain Copilot.\n\n"
                f"To get started, please send your **Employee Code** "
                f"(e.g. `EMP001`) so I can identify you.")
        _save_telegram_session(
            chat_id=chat_id,
            sales_person_id=person["sales_person_id"] if person else "",
            agent_session_id=str(uuid.uuid4()),
            last_message="/start",
        )
        return {"statusCode": 200, "body": "ok"}

    # ── Registration flow ─────────────────────────────────────────────────────
    person = lookup_sales_person_by_telegram(user_id)
    if not person:
        if text.upper().startswith("EMP") and len(text.strip()) <= 10:
            registered = register_telegram_user(
                employee_code=text.strip(),
                telegram_user_id=user_id,
                telegram_chat_id=chat_id,
            )
            if registered:
                role_label = "Manager" if registered["role"] == "MANAGER" else "Sales Rep"
                send_message(chat_id,
                    f"Registered! Welcome, **{registered['name']}** ({role_label}).\n\n"
                    f"You're all set. How can I help you today?")
            else:
                send_message(chat_id,
                    f"Employee code `{text.strip().upper()}` not found.\n\n"
                    f"Please check your code and try again, or contact your manager.")
        else:
            send_message(chat_id,
                f"You're not registered yet.\n\n"
                f"Please send your **Employee Code** (e.g. `EMP001`) to get started.")
        return {"statusCode": 200, "body": "ok"}

    # Not a fast-path message → needs Bedrock
    return None


# ─── Telegram: Bedrock handler (async — slow) ────────────────────────────────

def _handle_telegram_bedrock(body: dict, context=None) -> dict:
    """
    Process a Telegram message that requires Bedrock agent invocation.
    Called from async self-invocation. Sends reply via Telegram API.
    """
    from shared.telegram_utils import (
        parse_telegram_update, send_message, send_typing_action,
    )
    from shared.db_utils import (
        lookup_sales_person_by_telegram, get_session,
    )

    update = parse_telegram_update(body)
    if not update:
        return {"statusCode": 200, "body": "ok"}

    chat_id = update["chat_id"]
    user_id = update["user_id"]
    text    = update["text"]
    update_id = str(body.get("update_id", ""))

    # ── Deduplication: skip if this update_id was already processed ────────
    # Lambda Event invocations retry up to 2x on failure.
    # Check session's last_message to detect retries of the same update.
    existing_session = get_session(chat_id)
    if existing_session:
        ctx = existing_session.get("context")
        if isinstance(ctx, str):
            import json as _json
            try:
                ctx = _json.loads(ctx)
            except Exception:
                ctx = {}
        if isinstance(ctx, dict) and ctx.get("last_update_id") == update_id:
            logger.info(f"⏭️  Skipping duplicate update_id={update_id}")
            return {"statusCode": 200, "body": "ok"}

    person = lookup_sales_person_by_telegram(user_id)
    if not person:
        return {"statusCode": 200, "body": "ok"}

    role = person.get("role", "REP")
    sales_person_id = person.get("sales_person_id", "")

    # Reuse existing Bedrock session if available (30-min native expiry)
    if existing_session and existing_session.get("agent_session_id"):
        agent_session_id = existing_session["agent_session_id"]
    else:
        agent_session_id = str(uuid.uuid4())

    if role == "MANAGER":
        enriched_message = _build_manager_context(user_id, text)
    else:
        enriched_message = _build_rep_context(user_id, text)

    send_typing_action(chat_id)

    try:
        result = _invoke_agent(enriched_message, agent_session_id, context=context)
        reply_text = result["text"]
    except Exception as e:
        logger.error(f"❌ Bedrock invocation failed for chat_id={chat_id}: {e}", exc_info=True)
        reply_text = "Sorry, I'm having trouble right now. Please try again in a moment."

    send_message(chat_id, reply_text)

    # Save session with update_id for dedup on retries
    from shared.db_utils import save_session
    save_session(
        telegram_chat_id=chat_id,
        sales_person_id=sales_person_id,
        agent_session_id=agent_session_id,
        context={"last_update_id": update_id},
        last_message=text,
    )

    return {"statusCode": 200, "body": "ok"}


# ─── Dashboard chat handler ───────────────────────────────────────────────────

def _process_dashboard_chat(body: dict, context=None) -> dict:
    """Core dashboard chat logic (manager-only web UI)."""
    from shared.db_utils import get_manager_telegram_chat_id

    message    = body.get("message", body.get("query", "")).strip()
    session_id = body.get("session_id", str(uuid.uuid4()))
    source     = body.get("source", "")

    if not message:
        return {"text": "Please provide a message.", "agent": "System"}

    if not AGENT_ID or not AGENT_ALIAS_ID:
        return {"text": "Bedrock agent not configured.", "agent": "System"}

    # Resolve manager identity from DB for context header
    manager_telegram_id = "MANAGER"
    try:
        from shared.db_utils import get_db, row_to_dict
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT telegram_user_id FROM sales_persons WHERE role = 'MANAGER' AND is_active = TRUE LIMIT 1"
            )
            row = row_to_dict(cur.fetchone())
            if row and row.get("telegram_user_id"):
                manager_telegram_id = row["telegram_user_id"]
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"Could not resolve manager telegram_user_id: {e}")

    if source == "dashboard":
        logger.info(f"📊 Dashboard request — injecting manager context (user_id={manager_telegram_id})")
        message = _build_manager_context(manager_telegram_id, message)

    try:
        result = _invoke_agent(message, session_id, context=context)
        _save_web_session(session_id, session_id, message, result)
        return result
    except Exception as e:
        logger.error(f"❌ Agent error: {type(e).__name__}: {e}", exc_info=True)
        return {
            "text": "I'm having trouble connecting to the agents right now. Please try again in a moment.",
            "agent": "System",
            "session_id": session_id,
        }


# ─── Lambda entry point ───────────────────────────────────────────────────────

def lambda_handler(event, context):
    """
    Main entry point.
    - Telegram webhook updates  → _handle_telegram_update()
    - Everything else (dashboard, API Gateway /api/chat) → _process_dashboard_chat()
    """
    logger.info(f"📥 Handler invoked | Request ID: {context.aws_request_id}")

    http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    domain      = event.get("requestContext", {}).get("domainName", "")
    is_function_url = "lambda-url" in domain

    # CORS preflight
    if http_method == "OPTIONS":
        headers = {"Content-Type": "application/json"} if is_function_url else CORS_HEADERS
        return {"statusCode": 200, "headers": headers, "body": ""}

    # Parse body
    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        body = {}

    # ── Async self-invocation: do the actual Bedrock work ─────────────────────
    # When Lambda invokes itself asynchronously, the event has "_async_tg": True
    # at the top level (not inside "body"). Process directly without returning 200.
    if event.get("_async_tg"):
        return _handle_telegram_bedrock(json.loads(event.get("body", "{}")), context=context)

    # ── Telegram webhook (from Telegram servers) ───────────────────────────────
    if "update_id" in body:
        # Validate webhook secret token
        from shared.telegram_utils import validate_secret_token
        if WEBHOOK_SECRET and not validate_secret_token(event, WEBHOOK_SECRET):
            logger.warning("⛔ Invalid webhook secret token — rejecting request")
            return {"statusCode": 403, "body": "Forbidden"}

        # Try fast path first (/start, registration — no Bedrock needed)
        fast_result = _handle_telegram_fast(body)
        if fast_result is not None:
            logger.info(f"⚡ Fast path handled update_id={body.get('update_id')}")
            return fast_result

        # Slow path: needs Bedrock — fire async self-invocation and return 200
        # immediately so Telegram doesn't retry (60s timeout, Bedrock takes 50-60s).
        try:
            lambda_client = boto3.client("lambda", region_name=REGION)
            lambda_client.invoke(
                FunctionName=context.function_name,
                InvocationType="Event",   # async, no waiting for response
                Payload=json.dumps({
                    "_async_tg": True,
                    "body": event.get("body", "{}"),
                    "headers": event.get("headers", {}),
                }).encode("utf-8"),
            )
            logger.info(f"🔀 Async self-invocation dispatched for update_id={body.get('update_id')}")
        except Exception as e:
            # If async invocation fails, fall back to synchronous processing
            logger.warning(f"⚠️  Async invoke failed ({e}), processing synchronously")
            return _handle_telegram_bedrock(body, context=context)

        return {"statusCode": 200, "body": "ok"}

    # Dashboard / API Gateway chat
    result = _process_dashboard_chat(body, context=context)

    if is_function_url:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result),
        }
    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps(result),
    }
