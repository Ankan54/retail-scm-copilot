"""
Visit Action Group Lambda Handler (PostgreSQL version)
Handles: create_visit_record, create_commitment, get_recent_visits
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

        # Get product description
        product_row = _fetchone(conn,
            "SELECT short_name FROM products WHERE product_id = %s",
            (params["product_id"],))
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
             params["product_id"], product_desc, qty, today_str, expected_date,
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
