"""
Analytics Action Group Lambda Handler (PostgreSQL version)
Handles: get_team_overview, get_at_risk_dealers, get_commitment_pipeline, get_dealer_map_data, get_production_demand_supply
Read-only operations for the manager dashboard and React frontend.
"""
import json
import sys
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sys.path.insert(0, "/opt/python")
sys.path.insert(0, "/var/task")

from shared.db_utils import get_db, bedrock_response, rows_to_list, row_to_dict, today


def lambda_handler(event, context):
    logger.info(f"Event: {json.dumps(event, default=str)}")

    # Handle direct API Gateway calls (from React dashboard)
    if "httpMethod" in event or "requestContext" in event:
        return handle_rest_api(event)

    action_group = event.get("actionGroup", "analytics_actions")
    function = event.get("function", "")
    params = {p["name"]: p["value"] for p in event.get("parameters", [])}

    try:
        if function == "get_team_overview":
            result = get_team_overview(int(params.get("period_days", 30)))
        elif function == "get_at_risk_dealers":
            result = get_at_risk_dealers(params.get("sales_person_id"), int(params.get("limit", 10)))
        elif function == "get_commitment_pipeline":
            result = get_commitment_pipeline(params.get("sales_person_id"), params.get("status_filter"))
        elif function == "get_dealer_map_data":
            result = get_dealer_map_data(params.get("sales_person_id"))
        elif function == "get_production_demand_supply":
            result = get_production_demand_supply(params.get("period", "quarter"))
        else:
            result = {"error": f"Unknown function: {function}"}
    except KeyError as e:
        result = {"error": f"Missing required parameter: {e}"}
    except Exception as e:
        logger.exception(f"Error in {function}")
        result = {"error": str(e)}

    return bedrock_response(action_group, function, result)


def handle_rest_api(event):
    path = event.get("path", event.get("rawPath", ""))
    query_params = event.get("queryStringParameters") or {}

    try:
        if "/api/metrics" in path:
            data = get_team_overview(int(query_params.get("days", 30)))
        elif "/api/dealers" in path:
            data = get_dealer_map_data(query_params.get("rep_id"))
        elif "/api/commitments" in path:
            data = get_commitment_pipeline(query_params.get("rep_id"), query_params.get("status"))
        elif "/api/alerts" in path:
            data = get_active_alerts(query_params.get("rep_id"))
        elif "/api/map" in path:
            data = get_dealer_map_data(query_params.get("rep_id"))
        else:
            data = {"error": f"Unknown path: {path}"}

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
            },
            "body": json.dumps(data, default=str),
        }
    except Exception as e:
        logger.exception("REST API error")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def _fetchone(conn, sql, args=()):
    cur = conn.cursor()
    cur.execute(sql, args)
    return cur.fetchone()

def _fetchall(conn, sql, args=()):
    cur = conn.cursor()
    cur.execute(sql, args)
    return cur.fetchall()


# ─── get_team_overview ────────────────────────────────────────────────────────

def get_team_overview(period_days: int = 30) -> dict:
    conn = get_db()
    try:
        since = (datetime.now() - timedelta(days=period_days)).strftime("%Y-%m-%d")

        sales_row = _fetchone(conn,
            """
            SELECT COALESCE(SUM(total_amount), 0) AS total_sales,
                   COUNT(*) AS order_count,
                   COUNT(DISTINCT dealer_id) AS active_dealers
            FROM orders
            WHERE order_date >= %s AND status NOT IN ('CANCELLED', 'DRAFT')
            """,
            (since,))

        collection_row = _fetchone(conn,
            "SELECT COALESCE(SUM(amount), 0) AS total_collections FROM payments WHERE payment_date >= %s",
            (since,))

        rep_rows = _fetchall(conn,
            """
            SELECT sp.name AS rep_name, sp.sales_person_id,
                   COALESCE(SUM(o.total_amount), 0) AS sales,
                   COUNT(o.order_id) AS orders,
                   COUNT(DISTINCT v.visit_id) AS visits
            FROM sales_persons sp
            LEFT JOIN orders o ON sp.sales_person_id = o.sales_person_id AND o.order_date >= %s
            LEFT JOIN visits v ON sp.sales_person_id = v.sales_person_id AND v.visit_date >= %s
            WHERE sp.role = 'REP' AND sp.is_active = TRUE
            GROUP BY sp.sales_person_id, sp.name
            ORDER BY sales DESC
            """,
            (since, since))

        # Health distribution — use DISTINCT ON (PostgreSQL-native)
        health_rows = _fetchall(conn,
            """
            SELECT health_status, COUNT(*) AS count
            FROM (
                SELECT DISTINCT ON (dealer_id) dealer_id, health_status
                FROM dealer_health_scores
                ORDER BY dealer_id, calculated_date DESC
            ) AS latest
            GROUP BY health_status
            """)
        health_dist = {r["health_status"]: r["count"] for r in health_rows}

        overdue_row = _fetchone(conn,
            """
            SELECT COUNT(*) AS overdue_count,
                   COALESCE(SUM(total_amount - amount_paid), 0) AS overdue_amount
            FROM invoices
            WHERE status = 'OVERDUE' OR (status = 'PENDING' AND due_date < CURRENT_DATE::text)
            """)

        commit_row = _fetchone(conn,
            """
            SELECT COUNT(*) AS total_count,
                   COUNT(CASE WHEN status = 'CONVERTED' THEN 1 END) AS converted_count,
                   COUNT(CASE WHEN status IN ('PENDING', 'PARTIAL') THEN 1 END) AS pending_count,
                   SUM(CASE WHEN status IN ('PENDING', 'PARTIAL') THEN quantity_promised - COALESCE(converted_quantity, 0) ELSE 0 END) AS pending_qty,
                   SUM(quantity_promised) AS total_qty,
                   SUM(COALESCE(converted_quantity, 0)) AS converted_qty
            FROM commitments
            WHERE commitment_date >= %s
            """,
            (since,))

        total_commits = int(commit_row["total_count"] or 0)
        converted_commits = int(commit_row["converted_count"] or 0)
        conversion_rate = round(converted_commits / total_commits * 100, 1) if total_commits else 0

        total_qty = int(commit_row["total_qty"] or 0)
        converted_qty = int(commit_row["converted_qty"] or 0)
        qty_conversion_rate = round(converted_qty / total_qty * 100, 1) if total_qty else 0

        return {
            "success": True,
            "period_days": period_days,
            "sales": {
                "total_amount": float(sales_row["total_sales"] or 0),
                "order_count": int(sales_row["order_count"] or 0),
                "active_dealers": int(sales_row["active_dealers"] or 0),
            },
            "collections": {"total_amount": float(collection_row["total_collections"] or 0)},
            "rep_performance": rows_to_list(rep_rows),
            "dealer_health": {
                "HEALTHY": int(health_dist.get("HEALTHY", 0)),
                "AT_RISK": int(health_dist.get("AT_RISK", 0)),
                "CRITICAL": int(health_dist.get("CRITICAL", 0)),
            },
            "overdue_payments": {
                "count": int(overdue_row["overdue_count"] or 0),
                "amount": float(overdue_row["overdue_amount"] or 0),
            },
            "commitments": {
                "total": total_commits,
                "converted": converted_commits,
                "pending": int(commit_row["pending_count"] or 0),
                "pending_quantity": int(commit_row["pending_qty"] or 0),
                "conversion_rate_pct": conversion_rate,
                "total_quantity": total_qty,
                "converted_quantity": converted_qty,
                "quantity_conversion_rate_pct": qty_conversion_rate,
            },
        }
    finally:
        conn.close()


# ─── get_at_risk_dealers ──────────────────────────────────────────────────────

def get_at_risk_dealers(sales_person_id: str = None, limit: int = 10) -> dict:
    conn = get_db()
    try:
        sql = """
            SELECT d.dealer_id, d.name, d.category, d.district,
                   sp.name AS rep_name,
                   dhs.overall_score, dhs.health_status,
                   dhs.total_outstanding, dhs.days_since_last_order, dhs.attention_reason
            FROM dealers d
            JOIN (
                SELECT DISTINCT ON (dealer_id)
                       dealer_id, overall_score, health_status,
                       total_outstanding, days_since_last_order, attention_reason
                FROM dealer_health_scores
                WHERE health_status IN ('AT_RISK', 'CRITICAL')
                ORDER BY dealer_id, calculated_date DESC
            ) dhs ON d.dealer_id = dhs.dealer_id
            LEFT JOIN sales_persons sp ON d.sales_person_id = sp.sales_person_id
            WHERE d.status = 'ACTIVE'
        """
        args = []
        if sales_person_id:
            sql += " AND d.sales_person_id = %s"
            args.append(sales_person_id)
        sql += " ORDER BY dhs.overall_score ASC LIMIT %s"
        args.append(limit)

        rows = _fetchall(conn, sql, args)
        return {"success": True, "at_risk_dealers": rows_to_list(rows), "total": len(rows)}
    finally:
        conn.close()


# ─── get_commitment_pipeline ──────────────────────────────────────────────────

def get_commitment_pipeline(sales_person_id: str = None, status_filter: str = None) -> dict:
    conn = get_db()
    try:
        conditions = []
        args = []
        if sales_person_id:
            conditions.append("c.sales_person_id = %s")
            args.append(sales_person_id)
        if status_filter:
            conditions.append("c.status = %s")
            args.append(status_filter)
        else:
            conditions.append("c.status IN ('PENDING', 'PARTIAL', 'CONVERTED')")

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        sql = f"""
            SELECT
                c.commitment_id, c.commitment_date, c.expected_order_date,
                c.quantity_promised, c.converted_quantity, c.status,
                c.confidence_score,
                d.name AS dealer_name, d.category AS dealer_category,
                p.short_name AS product_name,
                sp.name AS rep_name,
                CASE WHEN c.expected_order_date < CURRENT_DATE::text AND c.status = 'PENDING' THEN 'OVERDUE'
                     WHEN c.expected_order_date <= (CURRENT_DATE + INTERVAL '3 days')::text AND c.status = 'PENDING' THEN 'DUE_SOON'
                     WHEN c.status = 'CONVERTED' THEN 'FULFILLED'
                     ELSE 'UPCOMING'
                END AS urgency_label
            FROM commitments c
            LEFT JOIN dealers d ON c.dealer_id = d.dealer_id
            LEFT JOIN products p ON c.product_id = p.product_id
            LEFT JOIN sales_persons sp ON c.sales_person_id = sp.sales_person_id
            {where}
            ORDER BY c.expected_order_date ASC LIMIT 100
        """
        rows = _fetchall(conn, sql, args)
        pipeline = rows_to_list(rows)
        pending = sum(1 for r in pipeline if r["status"] == "PENDING")
        due_soon = sum(1 for r in pipeline if r.get("urgency_label") == "DUE_SOON")
        overdue = sum(1 for r in pipeline if r.get("urgency_label") == "OVERDUE")

        return {
            "success": True,
            "commitments": pipeline,
            "summary": {"total": len(pipeline), "pending": pending, "due_soon": due_soon, "overdue": overdue},
        }
    finally:
        conn.close()


# ─── get_dealer_map_data ──────────────────────────────────────────────────────

def get_dealer_map_data(sales_person_id: str = None) -> dict:
    conn = get_db()
    try:
        sql = """
            SELECT d.dealer_id, d.name, d.latitude, d.longitude, d.category,
                   d.district, d.status, d.last_order_date, d.last_visit_date,
                   sp.name AS rep_name,
                   COALESCE(dhs.health_status, 'UNKNOWN') AS health_status,
                   COALESCE(dhs.overall_score, 50) AS health_score,
                   COALESCE(dhs.total_outstanding, 0) AS outstanding,
                   COALESCE(dhs.attention_reason, '') AS attention_reason
            FROM dealers d
            LEFT JOIN sales_persons sp ON d.sales_person_id = sp.sales_person_id
            LEFT JOIN (
                SELECT DISTINCT ON (dealer_id)
                       dealer_id, health_status, overall_score, total_outstanding, attention_reason
                FROM dealer_health_scores
                ORDER BY dealer_id, calculated_date DESC
            ) dhs ON d.dealer_id = dhs.dealer_id
            WHERE d.latitude IS NOT NULL AND d.longitude IS NOT NULL
        """
        args = []
        if sales_person_id:
            sql += " AND d.sales_person_id = %s"
            args.append(sales_person_id)
        sql += " ORDER BY d.name"

        dealers = _fetchall(conn, sql, args)
        warehouses = _fetchall(conn,
            "SELECT warehouse_id, name, code, latitude, longitude, city FROM warehouses WHERE is_active = TRUE")

        dealer_list = rows_to_list(dealers)
        color_map = {"HEALTHY": "green", "AT_RISK": "amber", "CRITICAL": "red", "UNKNOWN": "grey"}
        for d in dealer_list:
            d["map_color"] = color_map.get(d.get("health_status", "UNKNOWN"), "grey")

        return {
            "success": True,
            "dealers": dealer_list,
            "warehouses": rows_to_list(warehouses),
            "total_dealers": len(dealer_list),
        }
    finally:
        conn.close()


# ─── get_production_demand_supply ────────────────────────────────────────────

def get_production_demand_supply(period: str = "quarter") -> dict:
    """Production vs demand gap by month. period: 'quarter' (default), 'month', '6months'."""
    import calendar as cal
    conn = get_db()
    try:
        today_dt = datetime.now().date()

        if period == "month":
            start = today_dt.replace(day=1)
            end = today_dt.replace(day=cal.monthrange(today_dt.year, today_dt.month)[1])
        elif period == "6months":
            start = (today_dt - timedelta(days=180)).replace(day=1)
            end = today_dt
        else:  # quarter (default)
            q_start_month = ((today_dt.month - 1) // 3) * 3 + 1
            start = today_dt.replace(month=q_start_month, day=1)
            end_month = q_start_month + 2
            end_year = today_dt.year + (1 if end_month > 12 else 0)
            end_month = end_month - 12 if end_month > 12 else end_month
            end = today_dt.replace(year=end_year, month=end_month, day=cal.monthrange(end_year, end_month)[1])

        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        rows = _fetchall(conn, """
            WITH months AS (
                SELECT generate_series(
                    DATE_TRUNC('month', %s::date),
                    DATE_TRUNC('month', %s::date),
                    '1 month'
                )::date AS month_start
            ),
            produced AS (
                SELECT DATE_TRUNC('month', planned_date::date)::date AS m,
                       COALESCE(SUM(actual_qty), 0) AS produced
                FROM production_schedule
                WHERE planned_date >= %s AND planned_date <= %s
                  AND status != 'CANCELLED'
                GROUP BY m
            ),
            ordered AS (
                SELECT DATE_TRUNC('month', o.order_date::date)::date AS m,
                       COALESCE(SUM(oi.quantity_ordered), 0) AS ordered
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.order_id
                WHERE o.order_date >= %s AND o.order_date <= %s
                  AND o.status != 'CANCELLED'
                GROUP BY m
            ),
            committed AS (
                SELECT DATE_TRUNC('month', commitment_date::date)::date AS m,
                       COALESCE(SUM(quantity_promised), 0) AS committed
                FROM commitments
                WHERE commitment_date >= %s AND commitment_date <= %s
                GROUP BY m
            )
            SELECT
                TO_CHAR(ms.month_start, 'Mon YYYY') AS month,
                TO_CHAR(ms.month_start, 'YYYY-MM') AS ym,
                COALESCE(p.produced, 0) AS produced,
                COALESCE(o.ordered, 0) AS ordered,
                COALESCE(c.committed, 0) AS committed,
                COALESCE(o.ordered, 0) + COALESCE(c.committed, 0) AS total_demand,
                COALESCE(o.ordered, 0) + COALESCE(c.committed, 0) - COALESCE(p.produced, 0) AS demand_gap
            FROM months ms
            LEFT JOIN produced p  ON DATE_TRUNC('month', ms.month_start) = p.m
            LEFT JOIN ordered o   ON DATE_TRUNC('month', ms.month_start) = o.m
            LEFT JOIN committed c ON DATE_TRUNC('month', ms.month_start) = c.m
            ORDER BY ms.month_start
        """, (start_str, end_str, start_str, end_str, start_str, end_str, start_str, end_str))

        months_data = rows_to_list(rows)
        for r in months_data:
            r["produced"] = int(r.get("produced") or 0)
            r["ordered"] = int(r.get("ordered") or 0)
            r["committed"] = int(r.get("committed") or 0)
            r["total_demand"] = int(r.get("total_demand") or 0)
            r["demand_gap"] = int(r.get("demand_gap") or 0)

        total_produced = sum(r["produced"] for r in months_data)
        total_demand = sum(r["total_demand"] for r in months_data)
        total_gap = total_demand - total_produced

        return {
            "success": True,
            "period": period,
            "period_start": start_str,
            "period_end": end_str,
            "months": months_data,
            "summary": {
                "total_produced": total_produced,
                "total_demand": total_demand,
                "demand_gap": total_gap,
                "gap_pct": round(total_gap / total_demand * 100, 1) if total_demand else 0,
                "status": "SHORTFALL" if total_gap > 0 else "SURPLUS",
            },
        }
    finally:
        conn.close()


# ─── get_active_alerts ───────────────────────────────────────────────────────

def get_active_alerts(assigned_to: str = None) -> dict:
    conn = get_db()
    try:
        sql = """
            SELECT a.alert_id, a.alert_type, a.priority, a.title, a.message,
                   a.entity_type, a.entity_id, a.action_required,
                   a.created_at, a.status,
                   CASE WHEN a.entity_type = 'dealer' THEN d.name ELSE '' END AS entity_name,
                   sp.name AS assigned_to_name
            FROM alerts a
            LEFT JOIN dealers d ON a.entity_id = d.dealer_id
            LEFT JOIN sales_persons sp ON a.assigned_to = sp.sales_person_id
            WHERE a.status = 'ACTIVE'
        """
        args = []
        if assigned_to:
            sql += " AND a.assigned_to = %s"
            args.append(assigned_to)
        sql += """
            ORDER BY
                CASE a.priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                a.created_at DESC
            LIMIT 50
        """
        rows = _fetchall(conn, sql, args)
        return {"success": True, "alerts": rows_to_list(rows), "total": len(rows)}
    finally:
        conn.close()
