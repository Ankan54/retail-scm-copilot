"""
Order Action Group Lambda Handler (PostgreSQL version)
Handles: get_pending_commitments, consume_commitment, check_inventory,
         create_order, get_forecast_consumption, generate_alert
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
    action_group = event.get("actionGroup", "order_actions")
    function = event.get("function", "")
    params = {p["name"]: p["value"] for p in event.get("parameters", [])}

    try:
        if function == "get_pending_commitments":
            result = get_pending_commitments(params["dealer_id"], params.get("product_id"))
        elif function == "consume_commitment":
            result = consume_commitment(params["dealer_id"], params["product_id"], int(params["order_quantity"]))
        elif function == "check_inventory":
            result = check_inventory(params["product_id"], int(params["quantity"]))
        elif function == "create_order":
            result = create_order(params)
        elif function == "get_forecast_consumption":
            result = get_forecast_consumption(
                int(params.get("days_back", 30)),
                int(params.get("days_forward", 30)),
                params.get("product_id"),
            )
        elif function == "generate_alert":
            result = generate_alert(params)
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

def _fetchall(conn, sql, args=()):
    cur = conn.cursor()
    cur.execute(sql, args)
    return cur.fetchall()

def _exec(conn, sql, args=()):
    cur = conn.cursor()
    cur.execute(sql, args)
    return cur


# ─── get_pending_commitments ──────────────────────────────────────────────────

def get_pending_commitments(dealer_id: str, product_id: str = None) -> dict:
    conn = get_db()
    try:
        sql = """
            SELECT c.commitment_id, c.commitment_date, c.expected_order_date,
                   c.quantity_promised, c.converted_quantity, c.status,
                   c.confidence_score, c.product_description,
                   p.short_name AS product_name, p.product_code,
                   (c.quantity_promised - COALESCE(c.converted_quantity, 0)) AS remaining_qty,
                   CASE WHEN c.expected_order_date < CURRENT_DATE::text THEN 'OVERDUE'
                        WHEN c.expected_order_date <= (CURRENT_DATE + INTERVAL '3 days')::text THEN 'DUE_SOON'
                        ELSE 'UPCOMING'
                   END AS urgency
            FROM commitments c
            LEFT JOIN products p ON c.product_id = p.product_id
            WHERE c.dealer_id = %s AND c.status IN ('PENDING', 'PARTIAL')
        """
        args = [dealer_id]
        if product_id:
            sql += " AND c.product_id = %s"
            args.append(product_id)
        sql += " ORDER BY c.expected_order_date ASC"

        rows = _fetchall(conn, sql, args)
        return {
            "success": True,
            "dealer_id": dealer_id,
            "commitments": rows_to_list(rows),
            "total_pending": len(rows),
        }
    finally:
        conn.close()


# ─── consume_commitment ───────────────────────────────────────────────────────

def consume_commitment(dealer_id: str, product_id: str, order_quantity: int) -> dict:
    conn = get_db()
    try:
        today_str = today()
        forward_limit = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        ts = now_iso()

        commitments = _fetchall(conn,
            """
            SELECT commitment_id, quantity_promised, converted_quantity, expected_order_date,
                   (quantity_promised - COALESCE(converted_quantity, 0)) AS remaining_qty
            FROM commitments
            WHERE dealer_id = %s AND product_id = %s AND status IN ('PENDING', 'PARTIAL')
            ORDER BY expected_order_date ASC
            """,
            (dealer_id, product_id))

        remaining_order_qty = order_quantity
        consumed_details = []

        for c in commitments:
            if remaining_order_qty <= 0:
                break
            exp_date = str(c["expected_order_date"])
            remaining_commit = int(c["remaining_qty"] or 0)
            if remaining_commit <= 0:
                continue

            if exp_date <= today_str:
                consume_type = "backward"
            elif exp_date <= forward_limit:
                consume_type = "forward"
            else:
                break

            qty_to_consume = min(remaining_order_qty, remaining_commit)
            new_converted = (c["converted_quantity"] or 0) + qty_to_consume
            new_remaining = c["quantity_promised"] - new_converted
            new_status = "CONVERTED" if new_remaining <= 0 else "PARTIAL"

            _exec(conn,
                """
                UPDATE commitments
                SET converted_quantity = %s, status = %s, is_consumed = %s, updated_at = %s
                WHERE commitment_id = %s
                """,
                (new_converted, new_status, new_status == "CONVERTED", ts, c["commitment_id"]))

            consumed_details.append({
                "commitment_id": c["commitment_id"],
                "expected_date": exp_date,
                "consumed_qty": qty_to_consume,
                "status": new_status,
                "type": consume_type,
            })
            remaining_order_qty -= qty_to_consume

        conn.commit()
        conn.close()
        return {
            "success": True,
            "dealer_id": dealer_id,
            "product_id": product_id,
            "order_quantity": order_quantity,
            "consumed_from_commitments": order_quantity - remaining_order_qty,
            "unmatched_quantity": remaining_order_qty,
            "consumption_details": consumed_details,
            "fully_matched": remaining_order_qty == 0,
        }
    except Exception:
        conn.rollback()
        conn.close()
        raise


# ─── check_inventory ─────────────────────────────────────────────────────────

def check_inventory(product_id: str, quantity: int) -> dict:
    conn = get_db()
    try:
        inv_row = _fetchone(conn,
            "SELECT COALESCE(SUM(qty_on_hand), 0) AS on_hand, COALESCE(SUM(qty_reserved), 0) AS reserved FROM inventory WHERE product_id = %s",
            (product_id,))
        pending_row = _fetchone(conn,
            """
            SELECT COALESCE(SUM(oi.quantity_ordered), 0) AS pending_qty
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE oi.product_id = %s AND o.status IN ('DRAFT', 'CONFIRMED', 'PROCESSING')
            """,
            (product_id,))
        incoming_row = _fetchone(conn,
            """
            SELECT COALESCE(SUM(quantity), 0) AS incoming_qty
            FROM incoming_stock
            WHERE product_id = %s AND status = 'EXPECTED'
              AND expected_date <= (CURRENT_DATE + INTERVAL '7 days')::text
            """,
            (product_id,))
        product_row = _fetchone(conn,
            "SELECT short_name, reorder_level, safety_stock FROM products WHERE product_id = %s",
            (product_id,))

        on_hand = int(inv_row["on_hand"] or 0)
        reserved = int(inv_row["reserved"] or 0)
        pending = int(pending_row["pending_qty"] or 0)
        incoming = int(incoming_row["incoming_qty"] or 0)
        atp = on_hand - reserved - pending

        return {
            "success": True,
            "product_id": product_id,
            "product_name": product_row["short_name"] if product_row else "Unknown",
            "requested_quantity": quantity,
            "on_hand": on_hand,
            "reserved": reserved,
            "pending_orders": pending,
            "available_to_promise": atp,
            "incoming_in_7_days": incoming,
            "can_fulfill": atp >= quantity,
            "shortfall": max(0, quantity - atp) if atp < quantity else 0,
            "can_fulfill_with_incoming": (atp + incoming) >= quantity,
            "reorder_level": product_row["reorder_level"] if product_row else None,
        }
    finally:
        conn.close()


# ─── create_order ─────────────────────────────────────────────────────────────

def create_order(params: dict) -> dict:
    conn = get_db()
    try:
        order_id = str(uuid.uuid4())
        order_item_id = str(uuid.uuid4())
        ts = now_iso()
        today_str = today()

        product = _fetchone(conn,
            "SELECT dealer_price, units_per_case, short_name FROM products WHERE product_id = %s",
            (params["product_id"],))
        if not product:
            return {"error": f"Product not found: {params['product_id']}"}

        qty = int(params.get("quantity", 0))
        unit_price = float(product["dealer_price"] or 0)
        tax_rate = 18.0
        subtotal = unit_price * qty
        tax_amount = round(subtotal * tax_rate / 100, 2)
        total = round(subtotal + tax_amount, 2)

        count_row = _fetchone(conn, "SELECT COUNT(*) AS c FROM orders")
        order_num = f"ORD-{datetime.now().year}-{(count_row['c'] or 0) + 1:04d}"

        _exec(conn,
            """
            INSERT INTO orders (
                order_id, order_number, dealer_id, sales_person_id, order_date,
                requested_delivery_date, promised_delivery_date, subtotal,
                discount_amount, discount_percent, tax_amount, total_amount,
                status, payment_status, source, commitment_id, is_split,
                requires_approval, notes, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 0, %s, %s,
                      'CONFIRMED', 'UNPAID', 'FIELD', %s, FALSE, FALSE, %s, %s, %s)
            """,
            (order_id, order_num, params["dealer_id"], params["sales_person_id"],
             today_str,
             (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
             (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
             subtotal, tax_amount, total,
             params.get("commitment_id", ""),
             params.get("notes", ""), ts, ts))

        _exec(conn,
            """
            INSERT INTO order_items (
                order_item_id, order_id, product_id, quantity_ordered, quantity_confirmed,
                quantity_shipped, quantity_delivered, unit_price, discount_percent,
                discount_amount, tax_rate, tax_amount, line_total, created_at
            ) VALUES (%s, %s, %s, %s, %s, 0, 0, %s, 0, 0, %s, %s, %s, %s)
            """,
            (order_item_id, order_id, params["product_id"], qty, qty,
             unit_price, tax_rate, tax_amount, total, ts))

        if params.get("commitment_id"):
            _exec(conn,
                """
                UPDATE commitments SET converted_order_id = %s, consumed_by_order_id = %s,
                       conversion_date = %s, updated_at = %s
                WHERE commitment_id = %s
                """,
                (order_id, order_id, today_str, ts, params["commitment_id"]))

        _exec(conn,
            "UPDATE dealers SET last_order_date = %s, updated_at = %s WHERE dealer_id = %s",
            (today_str, ts, params["dealer_id"]))

        conn.commit()
        conn.close()
        return {
            "success": True,
            "order_id": order_id,
            "order_number": order_num,
            "product": product["short_name"],
            "quantity": qty,
            "total_amount": total,
            "status": "CONFIRMED",
            "message": f"Order {order_num} created: {qty} units of {product['short_name']}. Total: Rs.{total:,.2f}",
        }
    except Exception:
        conn.rollback()
        conn.close()
        raise


# ─── get_forecast_consumption ─────────────────────────────────────────────────

def get_forecast_consumption(days_back: int = 30, days_forward: int = 30, product_id: str = None) -> dict:
    conn = get_db()
    try:
        date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        date_to = (datetime.now() + timedelta(days=days_forward)).strftime("%Y-%m-%d")

        sql = """
            SELECT
                TO_CHAR(c.expected_order_date::date, 'IYYY-"W"IW') AS week,
                MIN(c.expected_order_date) AS week_start,
                p.short_name AS product_name,
                SUM(c.quantity_promised) AS committed_qty,
                SUM(COALESCE(c.converted_quantity, 0)) AS consumed_qty,
                COUNT(CASE WHEN c.status = 'CONVERTED' THEN 1 END) AS fulfilled_count,
                COUNT(CASE WHEN c.status = 'PENDING' AND c.expected_order_date < CURRENT_DATE::text THEN 1 END) AS missed_count,
                COUNT(*) AS total_commitments
            FROM commitments c
            LEFT JOIN products p ON c.product_id = p.product_id
            WHERE c.expected_order_date BETWEEN %s AND %s
        """
        args = [date_from, date_to]
        if product_id:
            sql += " AND c.product_id = %s"
            args.append(product_id)
        sql += " GROUP BY week, c.product_id, p.short_name ORDER BY week_start ASC"

        periods = _fetchall(conn, sql, args)
        periods_list = rows_to_list(periods)

        total_committed = sum(int(p.get("committed_qty") or 0) for p in periods_list)
        total_consumed = sum(int(p.get("consumed_qty") or 0) for p in periods_list)
        total_fulfilled = sum(int(p.get("fulfilled_count") or 0) for p in periods_list)
        total_missed = sum(int(p.get("missed_count") or 0) for p in periods_list)
        total_commitments = sum(int(p.get("total_commitments") or 0) for p in periods_list)

        return {
            "success": True,
            "period": {"from": date_from, "to": date_to},
            "periods": periods_list,
            "summary": {
                "total_committed_units": total_committed,
                "total_consumed_units": total_consumed,
                "consumption_rate_pct": round(total_consumed / total_committed * 100, 1) if total_committed > 0 else 0,
                "total_commitments": total_commitments,
                "fulfilled_commitments": total_fulfilled,
                "missed_commitments": total_missed,
                "fulfillment_rate_pct": round(total_fulfilled / total_commitments * 100, 1) if total_commitments > 0 else 0,
            },
        }
    finally:
        conn.close()


# ─── generate_alert ───────────────────────────────────────────────────────────

def generate_alert(params: dict) -> dict:
    conn = get_db()
    try:
        alert_id = str(uuid.uuid4())
        ts = now_iso()

        manager_row = _fetchone(conn,
            "SELECT sales_person_id FROM sales_persons WHERE role = 'MANAGER' LIMIT 1")
        manager_id = manager_row["sales_person_id"] if manager_row else None

        alert_type = params.get("alert_type", "GENERAL")
        priority = params.get("priority", "MEDIUM")
        entity_type = params.get("entity_type", "dealer")
        entity_id = params.get("entity_id", "")
        message = params.get("message", "Alert generated by agent")

        _exec(conn,
            """
            INSERT INTO alerts (
                alert_id, alert_type, priority, assigned_to, created_by,
                entity_type, entity_id, title, message, action_required,
                status, notification_sent, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, 'SYSTEM', %s, %s, %s, %s, 'Review and take appropriate action',
                      'ACTIVE', FALSE, %s, %s)
            """,
            (alert_id, alert_type, priority, manager_id,
             entity_type, entity_id,
             alert_type.replace("_", " ").title(),
             message, ts, ts))
        conn.commit()
        conn.close()
        return {
            "success": True,
            "alert_id": alert_id,
            "message": "Alert created for manager",
            "alert_type": alert_type,
            "priority": priority,
        }
    except Exception:
        conn.rollback()
        conn.close()
        raise
