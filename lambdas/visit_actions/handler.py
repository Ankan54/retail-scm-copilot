"""
Visit Action Group Lambda Handler (PostgreSQL version)
Handles: create_visit_record, create_commitment, get_recent_visits, send_manager_alert
"""
import json
import sys
import uuid
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sys.path.insert(0, "/opt/python")
sys.path.insert(0, "/var/task")

from shared.db_utils import get_db, bedrock_response, rows_to_list, row_to_dict, today, now_iso


def lambda_handler(event, context):
    logger.info(f"Event: {json.dumps(event, default=str)}")
    action_group = event.get("actionGroup", "visit_actions")
    function = event.get("function", "")
    params = {p["name"]: p["value"] for p in event.get("parameters", [])}

    try:
        if function == "create_visit_record":
            result = create_visit_record(params)
        elif function == "create_commitment":
            result = create_commitment(params)
        elif function == "get_recent_visits":
            result = get_recent_visits(params["dealer_id"], int(params.get("limit", 5)))
        elif function == "send_manager_alert":
            result = send_manager_alert(params)
        else:
            result = {"error": f"Unknown function: {function}"}
    except KeyError as e:
        result = {"error": f"Missing required parameter: {e}"}
    except Exception as e:
        logger.exception(f"Error in {function}")
        result = {"error": str(e)}

    return bedrock_response(action_group, function, result)


def _fetchone(conn, sql, args=()):
    cur = conn.cursor()
    cur.execute(sql, args)
    return cur.fetchone()


def _exec(conn, sql, args=()):
    cur = conn.cursor()
    cur.execute(sql, args)
    return cur


# ─── create_visit_record ──────────────────────────────────────────────────────

def create_visit_record(params: dict) -> dict:
    """Save a new visit record to the database."""
    conn = get_db()
    try:
        visit_id = str(uuid.uuid4())
        ts = now_iso()

        purpose = params.get("purpose", "ORDER")
        collection = float(params.get("collection_amount", 0))
        if collection > 0:
            outcome = "SUCCESSFUL"
        elif purpose == "COLLECTION" and collection == 0:
            outcome = "UNSUCCESSFUL"
        else:
            outcome = "SUCCESSFUL"

        raw_notes = params.get("raw_notes", "")
        next_action = params.get("next_action", "Schedule next visit")
        visit_date = params.get("visit_date", today())

        # Lookup sales_person_id from dealer
        sales_person_id = params.get("sales_person_id", "")
        if not sales_person_id:
            row = _fetchone(conn,
                "SELECT sales_person_id FROM dealers WHERE dealer_id = %s",
                (params["dealer_id"],))
            sales_person_id = row["sales_person_id"] if row else "UNKNOWN"

        next_visit_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        order_taken = purpose == "ORDER" and outcome == "SUCCESSFUL"
        follow_up = collection == 0 and purpose == "COLLECTION"

        _exec(conn,
            """
            INSERT INTO visits (
                visit_id, dealer_id, sales_person_id, visit_date, visit_type,
                purpose, check_in_time, check_out_time, duration_minutes,
                outcome, order_taken, collection_amount, next_action,
                next_visit_date, follow_up_required, raw_notes, source,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, 'PLANNED', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'TELEGRAM', %s, %s)
            """,
            (visit_id, params["dealer_id"], sales_person_id, visit_date,
             purpose, ts, ts, 15, outcome, order_taken, collection,
             next_action, next_visit_date, follow_up, raw_notes, ts, ts))

        _exec(conn,
            "UPDATE dealers SET last_visit_date = %s, updated_at = %s WHERE dealer_id = %s",
            (visit_date, ts, params["dealer_id"]))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "visit_id": visit_id,
            "sales_person_id": sales_person_id,
            "message": f"Visit recorded successfully. ID: {visit_id[:8]}",
            "visit_date": visit_date,
            "collection_amount": collection,
        }
    except Exception as e:
        logger.exception("Error creating visit record")
        conn.rollback()
        conn.close()
        raise


# ─── create_commitment ────────────────────────────────────────────────────────

def create_commitment(params: dict) -> dict:
    """Save a dealer commitment extracted from visit notes."""
    conn = get_db()
    try:
        commitment_id = str(uuid.uuid4())
        ts = now_iso()
        today_str = today()

        expected_date = params.get("expected_order_date", "")
        if not expected_date:
            expected_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        qty = int(params.get("quantity_promised", 0))
        confidence = float(params.get("confidence_score", 0.80))

        # Look up sales_person_id from the visit record
        visit_row = _fetchone(conn,
            "SELECT sales_person_id FROM visits WHERE visit_id = %s",
            (params["visit_id"],))
        sales_person_id = visit_row["sales_person_id"] if visit_row else "UNKNOWN"

        # Resolve product_id — accept either product_id (UUID) or product_code (CLN-500G)
        product_id_param = params.get("product_id", "")
        if "-" in product_id_param and len(product_id_param) < 20:  # Looks like product_code, not UUID
            # Resolve product_code -> product_id
            product_row = _fetchone(conn,
                "SELECT product_id, short_name FROM products WHERE product_code = %s",
                (product_id_param,))
            if not product_row:
                raise ValueError(f"Product code '{product_id_param}' not found. Use resolve_entity first or provide product_id (UUID).")
            product_id = product_row["product_id"]
            product_desc = product_row["short_name"]
        else:
            # Already UUID, just get description
            product_id = product_id_param
            product_row = _fetchone(conn,
                "SELECT short_name FROM products WHERE product_id = %s",
                (product_id,))
            product_desc = product_row["short_name"] if product_row else "Product"

        delivery_date = (datetime.strptime(expected_date, "%Y-%m-%d") + timedelta(days=2)).strftime("%Y-%m-%d")

        _exec(conn,
            """
            INSERT INTO commitments (
                commitment_id, visit_id, dealer_id, sales_person_id,
                product_id, product_description, quantity_promised,
                unit_of_measure, commitment_date, expected_order_date,
                expected_delivery_date, status, converted_quantity,
                confidence_score, extraction_source, is_consumed,
                notes, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'PCS', %s, %s, %s, 'PENDING', 0, %s, 'AI_EXTRACT', FALSE, %s, %s, %s)
            """,
            (commitment_id, params["visit_id"], params["dealer_id"], sales_person_id,
             product_id, product_desc, qty, today_str, expected_date,
             delivery_date, confidence, params.get("notes", ""), ts, ts))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "commitment_id": commitment_id,
            "message": f"Commitment saved: {qty} units of {product_desc} by {expected_date}",
            "product": product_desc,
            "quantity": qty,
            "expected_date": expected_date,
        }
    except Exception as e:
        logger.exception("Error creating commitment")
        conn.rollback()
        conn.close()
        raise


# ─── get_recent_visits ────────────────────────────────────────────────────────

def get_recent_visits(dealer_id: str, limit: int = 5) -> dict:
    """Get recent visit history for a dealer."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT v.visit_date, v.purpose, v.outcome, v.collection_amount,
                   v.next_action, v.raw_notes, v.follow_up_required,
                   sp.name AS rep_name
            FROM visits v
            LEFT JOIN sales_persons sp ON v.sales_person_id = sp.sales_person_id
            WHERE v.dealer_id = %s
            ORDER BY v.visit_date DESC LIMIT %s
            """,
            (dealer_id, limit))
        visits = cur.fetchall()
        return {"success": True, "dealer_id": dealer_id, "recent_visits": rows_to_list(visits)}
    finally:
        conn.close()


# ─── send_manager_alert ───────────────────────────────────────────────────────

def send_manager_alert(params: dict) -> dict:
    """
    Create an alert record and send Telegram notification to the manager.
    Called by Visit Capture Agent when it detects complaints, payment issues, or supply concerns.
    """
    dealer_id  = params.get("dealer_id", "")
    alert_type = params.get("alert_type", "DEALER_ISSUE")
    message    = params.get("message", "")
    priority   = params.get("priority", "HIGH")

    if not dealer_id or not message:
        return {"error": "dealer_id and message are required"}

    logger.info(f"[ALERT] send_manager_alert called: type={alert_type}, dealer={dealer_id}, priority={priority}")

    conn = get_db()
    try:
        ts = now_iso()
        alert_id = str(uuid.uuid4())

        # Lookup dealer and rep names for the notification
        dealer_row = _fetchone(conn, "SELECT name, sales_person_id FROM dealers WHERE dealer_id = %s", (dealer_id,))
        dealer_name = dealer_row["name"] if dealer_row else "Unknown Dealer"
        sales_person_id = dealer_row["sales_person_id"] if dealer_row else None

        rep_name = "Unknown Rep"
        if sales_person_id:
            rep_row = _fetchone(conn, "SELECT name FROM sales_persons WHERE sales_person_id = %s", (sales_person_id,))
            rep_name = rep_row["name"] if rep_row else "Unknown Rep"

        logger.info(f"[ALERT] dealer={dealer_name}, rep={rep_name}")

        # Insert alert row (using actual alerts table schema)
        alert_title = alert_type.replace("_", " ").title()
        _exec(conn,
            """
            INSERT INTO alerts (
                alert_id, alert_type, entity_type, entity_id,
                title, message, priority, status,
                created_by, notification_sent,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s)
            """,
            (alert_id, alert_type, "dealer", dealer_id,
             alert_title, message, priority, "ACTIVE",
             rep_name, ts, ts))
        conn.commit()
        logger.info(f"[ALERT] Alert row inserted: {alert_id}")

        # Send Telegram notification to manager
        emoji_map = {
            "DEALER_COMPLAINT": "🔴",
            "PAYMENT_CONCERN":  "💰",
            "SUPPLY_ISSUE":     "📦",
            "DEALER_AT_RISK":   "🔴",
        }
        emoji = emoji_map.get(alert_type, "⚠️")
        alert_title = alert_type.replace("_", " ").title()

        tg_sent = False
        try:
            from shared.db_utils import get_manager_telegram_chat_id, mark_alert_sent
            from shared.telegram_utils import send_message

            manager_chat_id = get_manager_telegram_chat_id()
            logger.info(f"[ALERT] manager_chat_id={manager_chat_id!r}")

            if manager_chat_id:
                tg_text = (
                    f"{emoji} <b>{alert_title}</b>\n\n"
                    f"<b>Dealer:</b> {dealer_name}\n"
                    f"<b>Rep:</b> {rep_name}\n\n"
                    f"{message}\n\n"
                    f"<b>Priority:</b> {priority}"
                )
                ok = send_message(manager_chat_id, tg_text, parse_mode="HTML")
                logger.info(f"[ALERT] send_message result: {ok}")
                if ok:
                    mark_alert_sent(alert_id)
                    tg_sent = True
                    logger.info(f"[ALERT] Manager Telegram alert sent successfully")
                else:
                    logger.warning("[ALERT] send_message returned False — check bot token / chat ID")
            else:
                logger.warning("[ALERT] No manager_chat_id in DB — skipping Telegram notification")
        except Exception as tg_err:
            logger.exception(f"[ALERT] Telegram send failed: {tg_err}")

        conn.close()
        return {
            "success": True,
            "alert_id": alert_id,
            "alert_type": alert_type,
            "telegram_sent": tg_sent,
            "message": f"Alert created for {dealer_name}. Manager {'notified via Telegram' if tg_sent else 'notification pending'}.",
        }

    except Exception as e:
        logger.exception("Error in send_manager_alert")
        conn.rollback()
        conn.close()
        return {"error": str(e)}
