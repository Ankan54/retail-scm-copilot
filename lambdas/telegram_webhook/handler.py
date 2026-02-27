"""
Chat Lambda Handler — Bedrock Supervisor Agent invocation (BUFFERED mode).

- Collects traces and text chunks during Bedrock invocation
- Logs all events to CloudWatch in real-time (viewable via Live Tail)
- Returns buffered response with all traces for frontend animation
- Frontend animates traces with 200ms delays for smooth UX
- Dashboard requests: manager identity context is prepended to the message
"""
import os
import json
import logging
import uuid
import time

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AGENT_ID = os.environ.get("BEDROCK_AGENT_ID", "")
AGENT_ALIAS_ID = os.environ.get("BEDROCK_AGENT_ALIAS_ID", "")
REGION = os.environ.get("REGION", "us-east-1")

# Manager identity — dashboard is manager-only
MANAGER_TELEGRAM_USER_ID = "8792879677"

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
}


def _build_manager_context(message: str) -> str:
    """
    Prepend manager identity + scope context for requests from the web dashboard.
    The Supervisor agent uses this to return company-wide results, not rep-specific.
    """
    return (
        f"[MANAGER DASHBOARD QUERY]\n"
        f"Caller: telegram_user_id={MANAGER_TELEGRAM_USER_ID}, role=MANAGER\n"
        f"Scope: This query is from the Sales/Production Manager. "
        f"Return company-wide aggregated results across ALL sales reps and territories. "
        f"Do NOT filter by individual sales rep. Show collective team and business performance.\n"
        f"---\n"
        f"{message}"
    )


def _get_bedrock_client():
    return boto3.client("bedrock-agent-runtime", region_name=REGION)


def _invoke_agent(message: str, session_id: str) -> dict:
    """
    Invoke the Bedrock Supervisor Agent.
    Logs all events to CloudWatch in real-time.
    Returns { text, agent, session_id, traces[] }.
    """
    logger.info(f"🚀 Starting agent invocation | Session: {session_id}")
    logger.info(f"📝 User message: {message}")

    start_time = time.time()
    client = _get_bedrock_client()

    response = client.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID,
        sessionId=session_id,
        inputText=message,
        enableTrace=True,
    )

    full_text = ""
    agent_name = "Supervisor"
    traces = []
    event_count = 0

    for event in response["completion"]:
        event_count += 1
        elapsed = time.time() - start_time

        # Text chunk
        if "chunk" in event:
            chunk = event["chunk"]
            if "bytes" in chunk:
                text = chunk["bytes"].decode("utf-8")
                full_text += text
                # Log chunk (truncated for readability)
                chunk_preview = text[:80].replace('\n', ' ')
                logger.info(f"💬 [{elapsed:.2f}s] CHUNK: {chunk_preview}...")

        # Trace event
        if "trace" in event:
            trace = event["trace"].get("trace", {})
            orch = trace.get("orchestrationTrace", {})
            invocation_input = orch.get("invocationInput", {})

            # Sub-agent routing
            collab = invocation_input.get("agentCollaboratorInvocationInput", {})
            if collab.get("agentCollaboratorName"):
                agent_name = collab["agentCollaboratorName"].replace("_", " ")
                logger.info(f"🤖 [{elapsed:.2f}s] ROUTING: → {agent_name}")
                traces.append({
                    "type": "agent",
                    "step": f"Routing to {agent_name}...",
                    "agent": agent_name,
                })

            # Tool/function call
            action_group = invocation_input.get("actionGroupInvocationInput", {})
            if action_group.get("function"):
                tool_name = action_group["function"]
                params = action_group.get("parameters", [])
                logger.info(f"🔧 [{elapsed:.2f}s] TOOL CALL: {tool_name} | Params: {len(params)}")
                traces.append({
                    "type": "tool",
                    "step": f"Calling {tool_name}...",
                    "tool": tool_name,
                })

            # Code interpreter
            code_interp = invocation_input.get("codeInterpreterInvocationInput", {})
            if code_interp:
                logger.info(f"🧮 [{elapsed:.2f}s] CODE INTERPRETER: Running calculation")
                traces.append({
                    "type": "tool",
                    "step": "Running calculation...",
                    "tool": "CodeInterpreter",
                })

            # Observation (tool results)
            observation = orch.get("observation", {})
            if observation:
                obs_type = observation.get("type", "unknown")
                logger.info(f"👁️  [{elapsed:.2f}s] OBSERVATION: {obs_type}")

            # Rationale (agent thinking)
            rationale = orch.get("rationale", {})
            if rationale.get("text"):
                thinking = rationale["text"][:100].replace('\n', ' ')
                logger.info(f"💭 [{elapsed:.2f}s] THINKING: {thinking}...")

    total_time = time.time() - start_time
    logger.info(f"✅ Agent invocation complete | Time: {total_time:.2f}s | Events: {event_count}")
    logger.info(f"📊 Final agent: {agent_name} | Traces: {len(traces)} | Response length: {len(full_text)} chars")

    return {
        "text": full_text.strip() or "I'm sorry, I couldn't generate a response. Please try again.",
        "agent": agent_name,
        "session_id": session_id,
        "traces": traces,
    }


def _save_session(session_id: str, agent_session_id: str,
                   user_msg: str, assistant_msg: dict):
    """Save conversation to PostgreSQL for page-refresh persistence."""
    try:
        from shared.db_utils import get_web_session, save_web_session

        existing = get_web_session(session_id)
        messages = []
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
        logger.info(f"💾 Session saved to database | Session: {session_id}")
    except Exception as e:
        logger.warning(f"⚠️  Failed to save session: {e}")


def _process_chat(body: dict) -> dict:
    """Core chat logic."""
    message = body.get("message", body.get("query", "")).strip()
    session_id = body.get("session_id", str(uuid.uuid4()))
    source = body.get("source", "")

    if not message:
        return {"text": "Please provide a message.", "agent": "System"}

    if not AGENT_ID or not AGENT_ALIAS_ID:
        return {"text": "Bedrock agent not configured.", "agent": "System"}

    # Inject manager context for all dashboard requests
    if source == "dashboard":
        logger.info(f"📊 Dashboard request — injecting manager context (user_id={MANAGER_TELEGRAM_USER_ID})")
        message = _build_manager_context(message)

    try:
        result = _invoke_agent(message, session_id)
        _save_session(session_id, session_id, message, result)
        return result
    except Exception as e:
        logger.error(f"❌ Agent invocation error: {e}", exc_info=True)
        return {
            "text": "I'm having trouble connecting to the agents right now. Please try again in a moment.",
            "agent": "System",
            "session_id": session_id,
        }


def lambda_handler(event, context):
    """
    Main entry point. Detects API Gateway vs Function URL and returns
    the appropriate response format.
    """
    logger.info(f"📥 Handler invoked | Request ID: {context.aws_request_id}")

    # Handle CORS preflight
    http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    domain = event.get("requestContext", {}).get("domainName", "")
    is_function_url = "lambda-url" in domain

    if http_method == "OPTIONS":
        headers = {"Content-Type": "application/json"} if is_function_url else CORS_HEADERS
        return {"statusCode": 200, "headers": headers, "body": ""}

    # Parse body
    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        body = {}

    result = _process_chat(body)

    if is_function_url:
        # Function URL: CORS headers added by service
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result),
        }
    else:
        # API Gateway: Lambda adds CORS headers
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(result),
        }
