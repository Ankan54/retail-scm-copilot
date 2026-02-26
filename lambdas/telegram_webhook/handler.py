"""
Telegram Webhook Lambda Handler (Phase 2 - placeholder for now)
This will be fully implemented after Bedrock agents are tested.
"""
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Telegram webhook handler - Phase 2 placeholder."""
    logger.info(f"Event: {json.dumps(event, default=str)}")

    # Handle direct chat API (for agent testing without Telegram)
    if "body" in event:
        try:
            body = json.loads(event.get("body", "{}"))
            query = body.get("message", body.get("query", ""))
            if query:
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    "body": json.dumps({
                        "status": "pending",
                        "message": "Telegram integration coming in Phase 2. Test agents directly via infra/test_agent.py",
                        "received_query": query,
                    }),
                }
        except Exception:
            pass

    return {
        "statusCode": 200,
        "body": json.dumps({"status": "ok", "phase": "2-pending"}),
    }
